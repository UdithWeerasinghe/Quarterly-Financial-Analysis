from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import os
import logging
from rag_pipeline import FinancialRAG
from langgraph.graph import StateGraph, END
from langchain_ollama.llms import OllamaLLM
from typing import TypedDict, List, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Update the path to use the correct relative path
DATA_PATH = os.path.join(os.path.dirname(__file__), "data_collection", "quarterly_financials.csv")
df = pd.read_csv(DATA_PATH, parse_dates=["TableDate"], dayfirst=True)
df = df.sort_values("TableDate")

# Initialize the RAG pipeline and LLM
rag = FinancialRAG()
if not rag.load_index("faiss.index", "faiss_meta.pkl"):
    rag.build_index_from_pdfs("backend/data_collection/downloaded_pdfs")
    rag.build_index_from_csv("backend/data_collection/quarterly_financials.csv")
    rag.save_index("faiss.index", "faiss_meta.pkl")
llm = OllamaLLM(model="llama3.2:3b")

# --- LangGraph Agentic Pipeline ---
class AgentState(TypedDict, total=False):
    query: str
    clarified_query: str
    search_results: List[Any]
    final_response: str

def clarify_node(state):
    query = state["query"]
    if len(query.split()) < 3:
        prompt = f"Expand this user query for a financial assistant: '{query}'"
        try:
            expanded = llm.invoke(prompt)
            if expanded and isinstance(expanded, str):
                query = expanded.strip()
        except Exception:
            pass
    return {**state, "clarified_query": query}

def search_node(state):
    query = state.get("clarified_query", state["query"])
    results = rag.search(query, k=5)
    print("DEBUG: Search results for query:", query)
    for r in results:
        print("  -", r.get("text", "")[:100])
    return {**state, "search_results": results}

def response_node(state):
    results = state.get("search_results", [])
    query = state.get("clarified_query", state["query"])
    if not results:
        return {**state, "final_response": "Sorry, I couldn't find any relevant information for your question."}
    context = "\n\n".join([f"Document {i+1}:\n{r['text']}" for i, r in enumerate(results)])
    answer = rag.generate_response(query, context)
    return {**state, "final_response": answer}

graph = StateGraph(AgentState)
graph.add_node("clarify_query", clarify_node)
graph.add_node("search_vectorstore", search_node)
graph.add_node("generate_response", response_node)
graph.add_edge("clarify_query", "search_vectorstore")
graph.add_edge("search_vectorstore", "generate_response")
graph.add_edge("generate_response", END)
graph.set_entry_point("clarify_query")
pipeline = graph.compile()

def run_agentic_pipeline(query):
    state = {"query": query}
    result = pipeline.invoke(state)
    return result["final_response"]

def get_relevant_context(question):
    """Extract relevant financial data based on the question."""
    try:
        context = []
        # Extract company names from the question
        companies = [company for company in df["Company"].unique() 
                    if company.lower() in question.lower()]
        # Extract metrics from the question
        metrics = ['revenue', 'profit', 'margin', 'ratio', 'growth', 'income']
        relevant_metrics = [metric for metric in metrics 
                           if metric.lower() in question.lower()]
        # Get relevant data
        for company in companies:
            company_data = df[df["Company"] == company]
            if not relevant_metrics:  # If no specific metrics mentioned, get all data
                context.append(f"{company} data:\n{company_data.to_string()}\n")
            else:
                # Filter for relevant metrics
                metric_cols = [col for col in company_data.columns 
                             if any(metric in col.lower() for metric in relevant_metrics)]
                if metric_cols:
                    context.append(f"{company} data:\n{company_data[metric_cols].to_string()}\n")
        return "\n".join(context)
    except Exception as e:
        logger.error(f"Error in get_relevant_context: {str(e)}")
        raise

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        if not data or "message" not in data:
            return jsonify({"error": "No message provided"}), 400
        question = data.get("message", "")
        logger.info(f"Received question: {question}")
        answer = run_agentic_pipeline(question)
        logger.info(f"Generated answer: {answer[:200]}...")
        return jsonify({"response": answer})
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

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

if __name__ == "__main__":
    app.run(debug=True)