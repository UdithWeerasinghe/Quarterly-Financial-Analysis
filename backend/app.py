from flask import Flask, jsonify, request, session
from flask_cors import CORS
import pandas as pd
import os
import logging
from rag_pipeline import RAGPipeline
from langgraph.graph import StateGraph, END
from langchain_ollama.llms import OllamaLLM
from typing import TypedDict, List, Any
import uuid

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Load and prepare data
df = pd.read_csv("backend/data_collection/quarterly_financials_cleaned.csv")
df["TableDate"] = pd.to_datetime(df["TableDate"])
df = df.sort_values("TableDate")

# Initialize RAG pipeline
try:
    rag_pipeline = RAGPipeline()
    logger.info("RAG pipeline initialized successfully")
except Exception as e:
    logger.error(f"Error initializing RAG pipeline: {str(e)}")
    raise

# Initialize LLM
llm = OllamaLLM(model="llama3.2:3b")

# Define state types
class GraphState(TypedDict):
    query: str
    clarified_query: str
    search_results: List[Any]
    final_response: str

# Define nodes
def search_node(state: GraphState) -> GraphState:
    query = state.get("clarified_query", state["query"])
    results = rag_pipeline.query(query)
    print("DEBUG: Search results for query:", query)
    for r in results:
        print(f"DEBUG: Result: {r}")
    return {**state, "search_results": results}

def generate_response_node(state: GraphState) -> GraphState:
    results = state["search_results"]
    query = state.get("clarified_query", state["query"])

    if not results:
        return {**state, "final_response": "Sorry, I couldn't find any relevant information for your question."}

    # Use the same normalize_result function as in your API
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

    # Format results for LLM
    context = "\n\n".join([
        f"Company: {r['company']}\n"
        f"Date: {r['date']}\n"
        f"Year: {r.get('year', 'N/A')}\n"
        f"Quarter: {r.get('quarter', 'N/A')}\n"
        f"Quarter Period: {r.get('quarter_period', 'N/A')}\n"
        + "\n".join([f"{metric}: {value:,.2f} LKR" for metric, value in r['metrics'].items()])
        for r in normalized_results
    ])

    # Generate response using LLM
    prompt = f"""You are a financial analyst assistant. Use the following financial data to answer the question.
If you can't answer with the given data, say so.

Quarter Definitions:
- Q1: January to March (ends March 31)
- Q2: April to June (ends June 30)
- Q3: July to September (ends September 30)
- Q4: October to December (ends December 31)

    Note: All values are in Sri Lankan Rupees (LKR) and needed to multiply by 1000 when giving the final answer.
    
    Question: {query}

Financial Data:
{context}

Answer:"""

    response = llm.invoke(prompt)
    return {**state, "final_response": response}

# Create graph
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("search", search_node)
workflow.add_node("generate_response", generate_response_node)

# Add edges
workflow.add_edge("search", "generate_response")
workflow.add_edge("generate_response", END)
workflow.set_entry_point("search")

# Compile graph
graph = workflow.compile()

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

# At the top of your app.py
user_sessions = {}

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
        
        # Run the graph
        result = graph.invoke({"query": question})
        results = result['search_results']
        normalized_results = [normalize_result(r) for r in results]
        
        # After answering:
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

@app.route("/")
def home():
    return "Quarterly Financial Analysis API is running."

@app.route("/api/companies")
def companies():
    companies = sorted(df["Company"].unique())
    return jsonify(companies)

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

def parse_query(question, user_context):
    # Try to extract company, metric, quarter, year from question
    # If missing, use from user_context
    company = extract_company(question) or user_context.get("last_company")
    metric = extract_metric(question) or user_context.get("last_metric")
    quarter = extract_quarter(question) or user_context.get("last_quarter")
    year = extract_year(question) or user_context.get("last_year")
    return company, metric, quarter, year

if __name__ == "__main__":
    app.run(debug=True)