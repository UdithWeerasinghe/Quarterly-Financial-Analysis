from flask import Flask, jsonify, request, session
from flask_cors import CORS
import pandas as pd
import os
import sys
import logging
import re

# Add the parent directory to Python path for module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the RAG pipeline and LLM tools
from backend.llm_driven_query_system.rag import RAGPipeline
from langgraph.graph import StateGraph, END
from langchain_ollama.llms import OllamaLLM
from typing import TypedDict, List, Any
import uuid
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Set up logging for the application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app and enable CORS for cross-origin requests
app = Flask(__name__)
CORS(app)

# Define base paths for data and PDF directories
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BACKEND_DIR, "dataset_creation", "cleaned_data")
PDF_DIR = os.path.join(BACKEND_DIR, "data_scraping", "pdfs")

# Load and prepare the cleaned financial data
# This CSV is expected to be created by the data pipeline
# and should contain all relevant financial information
# for the dashboard and chat system
#
df = pd.read_csv(os.path.join(DATA_DIR, "cleaned_quarterly_financials.csv"))
df["TableDate"] = pd.to_datetime(df["TableDate"])
df = df.sort_values("TableDate")

# Initialize the Retrieval-Augmented Generation (RAG) pipeline
try:
    pipeline = RAGPipeline()
    logger.info("RAG pipeline initialized successfully")
except Exception as e:
    logger.error(f"Error initializing RAG pipeline: {str(e)}")
    raise

# Initialize LLM
llm = OllamaLLM(model="llama3.2:3b")

# Create a prompt template for the LLM to ensure consistent, context-aware answers
prompt_template = PromptTemplate(
    input_variables=["question", "context"],
    template="""You are a helpful financial analyst assistant. Use the following context to answer the question.
    If you cannot find the answer in the context, say so. Always format numbers with commas and specify LKR currency.
    
    Context: {context}
    
    Question: {question}
    
    Answer:"""
)

# Create an LLM chain for generating answers
chain = LLMChain(llm=llm, prompt=prompt_template)

# Define the state type for the graph-based workflow
class GraphState(TypedDict):
    query: str
    clarified_query: str
    search_results: List[Any]
    final_response: str

# Node: Search for relevant results using the RAG pipeline
# This node takes a query and returns search results

def search_node(state: GraphState) -> GraphState:
    query = state.get("clarified_query", state["query"])
    results = pipeline.query(query)
    print("DEBUG: Search results for query:", query)
    for r in results:
        print(f"DEBUG: Result: {r}")
    return {**state, "search_results": results}

# Node: Generate a response using the LLM based on search results
# This node formats the results and uses the LLM to create a natural language answer

def generate_response_node(state: GraphState) -> GraphState:
    results = state["search_results"]
    query = state.get("clarified_query", state["query"])

    if not results:
        return {**state, "final_response": "Sorry, I couldn't find any relevant information for your question."}

    # Helper function to normalize a result dictionary
    def normalize_result(result):
        metrics = result.get('metrics') or {result.get('Metric'): result.get('Value')}
        metrics_lkr = {k: v * 1000 if v is not None else None for k, v in metrics.items()}
        return {
            "company": result.get('company') or result.get('Company'),
            "date": result.get('date') or result.get('TableDate'),
            "year": result.get('year') or result.get('Year'),
            "quarter": result.get('quarter') or result.get('QuarterName') or result.get('Quarter'),
            "quarter_period": result.get('quarter_period') or result.get('QuarterPeriod'),
            "metrics": metrics_lkr
        }

    normalized_results = [normalize_result(r) for r in results]

    # Format results for LLM context
    context = "\n\n".join([
        f"Company: {r['company']}\n"
        f"Date: {r['date']}\n"
        f"Year: {r.get('year', 'N/A')}\n"
        f"Quarter: {r.get('quarter', 'N/A')}\n"
        f"Quarter Period: {r.get('quarter_period', 'N/A')}\n"
        + "\n".join([
            f"{metric}: {value:,.2f} LKR" if value is not None else f"{metric}: N/A"
            for metric, value in r['metrics'].items()
        ])
        for r in normalized_results
    ])

    # Generate response using LLM
    response = chain.run(question=query, context=context)
    return {**state, "final_response": response}

# Create a graph workflow for the chat system
workflow = StateGraph(GraphState)

# Add nodes to the workflow
workflow.add_node("search", search_node)
workflow.add_node("generate_response", generate_response_node)

# Define the flow of the workflow
workflow.add_edge("search", "generate_response")
workflow.add_edge("generate_response", END)
workflow.set_entry_point("search")

# Compile the workflow graph
graph = workflow.compile()

# Helper function to normalize a result for API responses
def normalize_result(result):
    # Get the metrics dictionary (or create one from Metric/Value)
    metrics = result.get('metrics') or {result.get('Metric'): result.get('Value')}
    # Multiply all values by 1000 and format as LKR
    metrics_lkr = {k: v * 1000 if v is not None else None for k, v in metrics.items()}
    return {
        "company": result.get('company') or result.get('Company'),
        "date": result.get('date') or result.get('TableDate'),
        "year": result.get('year') or result.get('Year'),
        "quarter": result.get('quarter') or result.get('QuarterName') or result.get('Quarter'),
        "quarter_period": result.get('quarter_period') or result.get('QuarterPeriod'),
        "metrics": metrics_lkr
    }

# Dictionary to store user session context for conversational memory
user_sessions = {}

# API endpoint: Query the chat system with a question
@app.route("/api/query", methods=["POST"])
def query():
    session_id = request.json.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    user_context = user_sessions.get(session_id, {})
    try:
        data = request.get_json()
        question = data.get('question')
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        # Run the workflow graph to get results
        result = graph.invoke({"query": question})
        results = result['search_results']
        normalized_results = [normalize_result(r) for r in results]
        
        # Update user session context for follow-up questions
        user_sessions[session_id] = {
            "last_company": normalized_results[0]["company"],
            "last_metric": list(normalized_results[0]["metrics"].keys())[0],
            "last_quarter": normalized_results[0]["quarter"],
            "last_year": normalized_results[0]["year"],
            # ... any other context ...
        }
        return jsonify({
            'response': result['final_response'],
            'results': normalized_results,
            'session_id': session_id
        })
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({'error': str(e)}), 500

# API endpoint: Home page for health check
@app.route("/")
def home():
    return "Quarterly Financial Analysis API is running."

# API endpoint: Get list of companies
@app.route("/api/companies")
def companies():
    companies = sorted(df["Company"].unique())
    return jsonify(companies)

# API endpoint: Get metrics for a company (quarterly or annual)
@app.route("/api/metrics")
def metrics():
    company = request.args.get("company")
    period = request.args.get("period", "quarterly")
    dff = df[df["Company"] == company]
    if period == "annual":
        dff = dff.copy()
        dff["Year"] = pd.to_datetime(dff["TableDate"], errors='coerce').dt.year
        annual = dff.groupby("Year").sum(numeric_only=True).reset_index()
        annual["TableDate"] = pd.to_datetime(annual["Year"].astype(int).astype(str) + "-12-31")
        dff = annual
    return dff.to_json(orient="records", date_format="iso")

# API endpoint: Get comparison data for a company (quarterly or annual)
@app.route("/api/comparisons")
def comparisons():
    company = request.args.get("company")
    period = request.args.get("period", "quarterly")
    dff = df[df["Company"] == company]
    if period == "annual":
        dff = dff.copy()
        dff["Year"] = pd.to_datetime(dff["TableDate"], errors='coerce').dt.year
        # Sum all metrics for each year
        annual = dff.groupby("Year").sum(numeric_only=True).reset_index()
        annual["TableDate"] = pd.to_datetime(annual["Year"].astype(int).astype(str) + "-12-31")
        dff = annual
    return dff.to_json(orient="records", date_format="iso")

# API endpoint: Get financial ratios for a company (quarterly or annual)
@app.route("/api/ratios")
def ratios():
    company = request.args.get("company")
    period = request.args.get("period", "quarterly")
    dff = df[df["Company"] == company].copy()
    if period == "annual":
        dff["Year"] = pd.to_datetime(dff["TableDate"], errors='coerce').dt.year
        annual = dff.groupby("Year").agg({
            "Gross Profit": "sum",
            "Operating Income": "sum",
            "Net Income": "sum",
            "Revenue": "sum"
        }).reset_index()
        annual["Gross Margin"] = annual["Gross Profit"] / annual["Revenue"] * 100
        annual["Operating Margin"] = annual["Operating Income"] / annual["Revenue"] * 100
        annual["Net Margin"] = annual["Net Income"] / annual["Revenue"] * 100
        annual["TableDate"] = pd.to_datetime(annual["Year"].astype(int).astype(str) + "-12-31")
        return annual[["TableDate", "Gross Margin", "Operating Margin", "Net Margin"]].to_json(orient="records", date_format="iso")
    else:
        dff["Gross Margin"] = dff["Gross Profit"] / dff["Revenue"] * 100
        dff["Operating Margin"] = dff["Operating Income"] / dff["Revenue"] * 100
        dff["Net Margin"] = dff["Net Income"] / dff["Revenue"] * 100
        return dff[["TableDate", "Gross Margin", "Operating Margin", "Net Margin"]].to_json(orient="records", date_format="iso")

# Helper: Parse a query and extract company, metric, quarter, and year
# Uses regex and session context for conversational memory
def parse_query(question, user_context):
    company = extract_company(question) or user_context.get("last_company")
    metric = extract_metric(question) or user_context.get("last_metric")
    quarter = extract_quarter(question) or user_context.get("last_quarter")
    year = extract_year(question) or user_context.get("last_year")
    return company, metric, quarter, year

# Helper: Extract company name from question using regex
def extract_company(question):
    company_match = re.search(r'(REXP|DIPD)', question, re.IGNORECASE)
    return company_match.group().upper() if company_match else None

# Helper: Extract financial metric from question
def extract_metric(question):
    metrics = ['Revenue', 'COGS', 'Gross Profit', 'Operating Expenses', 'Operating Income', 'Net Income']
    for metric in metrics:
        if metric.lower() in question.lower():
            return metric
    return None

# Helper: Extract quarter information from question
def extract_quarter(question):
    quarter_match = re.search(r'(1st|2nd|3rd|4th|Q[1-4])', question, re.IGNORECASE)
    if quarter_match:
        quarter = quarter_match.group().capitalize()
        quarter_map = {
            '1st': 'Q1', '2nd': 'Q2', '3rd': 'Q3', '4th': 'Q4',
            'Q1': 'Q1', 'Q2': 'Q2', 'Q3': 'Q3', 'Q4': 'Q4'
        }
        return quarter_map.get(quarter)
    return None

# Helper: Extract year from question
def extract_year(question):
    year_match = re.search(r'20\d{2}', question)
    return int(year_match.group()) if year_match else None

# API endpoint: Chat interface for the LLM-powered assistant
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        question = data.get('question')
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        # Get relevant context from RAG pipeline
        results = pipeline.query(question)
        
        if not results:
            return jsonify({
                'answer': "I couldn't find any relevant information to answer your question. Please try rephrasing or asking about a different time period.",
                'context': "",
                'raw_results': []
            })
        
        # Format context from results for the LLM
        context = []
        for result in results:
            company = result.get('company') or result.get('Company')
            date = result.get('date') or result.get('TableDate')
            metrics = result.get('metrics') or {result.get('Metric'): result.get('Value')}
            
            context_entry = f"Company: {company}\nDate: {date}\n"
            for metric, value in metrics.items():
                if value is not None:
                    context_entry += f"{metric}: {value:,.2f} LKR\n"
            context.append(context_entry)
        
        context_str = "\n".join(context)
        
        try:
            # Generate response using LLM
            response = chain.run(question=question, context=context_str)
            
            return jsonify({
                'answer': response,
                'context': context_str,
                'raw_results': results
            })
        except Exception as llm_error:
            logger.error(f"Error generating LLM response: {str(llm_error)}")
            return jsonify({
                'answer': "I'm having trouble generating a response. Please try rephrasing your question.",
                'context': context_str,
                'raw_results': results
            })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'error': 'Failed to process your question. Please try again or rephrase your question.',
            'details': str(e)
        }), 500

# API endpoint: Health check for monitoring
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

# Run the Flask app if this file is executed directly
if __name__ == "__main__":
    app.run(debug=True)