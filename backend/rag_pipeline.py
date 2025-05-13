import os
import json
import logging
from pathlib import Path
import faiss
import numpy as np
import requests
from langchain_ollama.llms import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
import pdfplumber
import pickle

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinancialRAG:
    def __init__(self, model_name="llama3.2:3b"):
        """Initialize the RAG pipeline with Ollama and FAISS."""
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api"
        self.llm = OllamaLLM(model=model_name)
        
        # Initialize FAISS index
        self.index = None
        self.documents = []
        self.embedding_dimension = None
        
        # Test Ollama connection
        self._test_ollama_connection()
        
    def _test_ollama_connection(self):
        """Test connection to Ollama."""
        try:
            response = requests.post(
                f"{self.ollama_url}/embeddings",
                json={"model": self.model_name, "prompt": "test"}
            )
            if response.status_code != 200:
                raise Exception(f"Ollama API returned status code {response.status_code}")
            self.embedding_dimension = len(response.json()["embedding"])
            logger.info(f"Successfully connected to Ollama. Embedding dimension: {self.embedding_dimension}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {str(e)}")
            raise

    def get_embedding(self, text):
        """Get embedding from Ollama."""
        try:
            response = requests.post(
                f"{self.ollama_url}/embeddings",
                json={"model": self.model_name, "prompt": text}
            )
            if response.status_code == 200:
                return response.json()["embedding"]
            else:
                logger.error(f"Ollama API error: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return None

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF and split into chunks."""
        chunks = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        # Split text into smaller chunks
                        paragraphs = text.split('\n\n')
                        for para in paragraphs:
                            if len(para.strip()) > 50:  # Only keep substantial chunks
                                chunks.append(para.strip())
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {str(e)}")
        return chunks

    def prepare_document(self, text, metadata):
        """Prepare a document for indexing."""
        return {
            "text": text,
            "metadata": metadata
        }

    def build_index_from_pdfs(self, pdf_dir):
        """Build FAISS index from PDF files."""
        logger.info("Building index from PDFs...")
        
        pdf_dir = Path(pdf_dir)
        if not pdf_dir.exists():
            logger.error(f"PDF directory not found: {pdf_dir}")
            return
        
        documents = []
        
        # Process each PDF file
        for pdf_file in pdf_dir.glob("**/*.pdf"):
            logger.info(f"Processing {pdf_file.name}")
            
            # Extract company name from directory structure
            company = pdf_file.parent.name
            date = pdf_file.stem.split('_')[0] if '_' in pdf_file.stem else "Unknown"
            
            # Extract text chunks from PDF
            chunks = self.extract_text_from_pdf(pdf_file)
            
            # Create documents with metadata
            for chunk in chunks:
                metadata = {
                    'Company': company,
                    'Date': date,
                    'ReportName': pdf_file.name,
                    'Source': 'PDF'
                }
                documents.append(self.prepare_document(chunk, metadata))
        
        if documents:
            self._build_faiss_index(documents)
        else:
            logger.warning("No documents extracted from PDFs")

    def build_index_from_csv(self, csv_path):
        """Build FAISS index from CSV data."""
        logger.info("Building index from CSV...")
        
        try:
            df = pd.read_csv(csv_path, parse_dates=["TableDate"])
            
            documents = []
            for _, row in df.iterrows():
                # Create a text representation of the row
                text = f"""
                Company: {row['Company']}
                Date: {row['TableDate']}
                Revenue: {row.get('Revenue', 'N/A')}
                Gross Profit: {row.get('Gross Profit', 'N/A')}
                Operating Income: {row.get('Operating Income', 'N/A')}
                Net Income: {row.get('Net Income', 'N/A')}
                """.strip()
                
                metadata = row.to_dict()
                documents.append(self.prepare_document(text, metadata))
            
            if documents:
                self._build_faiss_index(documents)
            else:
                logger.warning("No documents created from CSV")
                
        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}")

    def _build_faiss_index(self, documents):
        """Build FAISS index from documents."""
        try:
            # Get embeddings for all documents
            embeddings = []
            for i, doc in enumerate(documents):
                if i % 10 == 0:  # Log progress every 10 documents
                    logger.info(f"Processing document {i+1}/{len(documents)}")
                embedding = self.get_embedding(doc["text"])
                if embedding:
                    embeddings.append(embedding)
                else:
                    logger.warning(f"Failed to get embedding for document {i+1}")
            
            if embeddings:
                # Create FAISS index
                self.index = faiss.IndexFlatL2(self.embedding_dimension)
                self.index.add(np.array(embeddings).astype('float32'))
                self.documents = documents
                logger.info(f"Built FAISS index with {len(embeddings)} documents")
            else:
                logger.error("No embeddings were created successfully")
                
        except Exception as e:
            logger.error(f"Error building FAISS index: {str(e)}")

    def search(self, query, k=5):
        """Search for similar documents."""
        if not self.index:
            logger.error("FAISS index not built")
            return []
        
        try:
            # Get query embedding
            query_embedding = self.get_embedding(query)
            if query_embedding is None:
                logger.error("Failed to get query embedding")
                return []
            
            # Search in FAISS
            distances, indices = self.index.search(
                np.array([query_embedding]).astype('float32'), k
            )
            
            # Return results with metadata
            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx != -1:  # FAISS returns -1 for empty slots
                    result = self.documents[idx].copy()
                    result['similarity_score'] = float(1 / (1 + distance))
                    results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return []

    def generate_response(self, query, context):
        """Generate a response using the LLM."""
        try:
            # Create prompt template
            template = """
            You are a financial analyst assistant. Use the following context to answer the question.
            
            Context:
            {context}
            
            Question: {query}
            
            Answer:
            """
            
            prompt = PromptTemplate(
                input_variables=["context", "query"],
                template=template
            )
            
            # Create chain
            chain = LLMChain(llm=self.llm, prompt=prompt)
            
            # Generate response
            response = chain.run(context=context, query=query)
            
            return response
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I apologize, but I encountered an error while generating the response."

    def query(self, user_query, k=3):
        """Query the RAG system."""
        try:
            # Search for relevant documents
            results = self.search(user_query, k=k)
            
            if not results:
                return "I couldn't find any relevant information to answer your question."
            
            # Prepare context from results
            context = "\n\n".join([
                f"Document {i+1}:\n{result['text']}\nRelevance: {result['similarity_score']:.2f}"
                for i, result in enumerate(results)
            ])
            
            # Generate response
            response = self.generate_response(user_query, context)
            
            return response
        except Exception as e:
            logger.error(f"Error in query: {str(e)}")
            return "I apologize, but I encountered an error while processing your query."

    def save_index(self, index_path="faiss.index", meta_path="faiss_meta.pkl"):
        if self.index is not None:
            faiss.write_index(self.index, index_path)
            with open(meta_path, "wb") as f:
                pickle.dump(self.documents, f)
            print(f"FAISS index and metadata saved to {index_path} and {meta_path}")

    def load_index(self, index_path="faiss.index", meta_path="faiss_meta.pkl"):
        if os.path.exists(index_path) and os.path.exists(meta_path):
            self.index = faiss.read_index(index_path)
            with open(meta_path, "rb") as f:
                self.documents = pickle.load(f)
            print(f"FAISS index and metadata loaded from {index_path} and {meta_path}")
            return True
        return False

def main():
    try:
        # Initialize RAG system
        rag = FinancialRAG()
        
        # Build indices
        pdf_dir = Path("backend/data_collection/downloaded_pdfs")
        csv_path = Path("backend/data_collection/quarterly_financials.csv")
        
        if pdf_dir.exists():
            rag.build_index_from_pdfs(pdf_dir)
        
        if csv_path.exists():
            rag.build_index_from_csv(csv_path)
        
        # Test queries
        test_queries = [
            "What was the latest revenue for Dipped Products?",
            "Compare the operating income between DIPD and REXP",
            "Show me the financial performance trends for the last quarter"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            response = rag.query(query)
            print(f"Response: {response}")
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main() 