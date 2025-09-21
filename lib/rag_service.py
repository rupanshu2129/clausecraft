import os
import uuid
from typing import List, Dict, Any
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

from .extract_text import extract_text

class RAGService:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="contracts_knowledge",
            metadata={"description": "Contract and SOW knowledge base"}
        )
    
    def add_documents(self, files: List[Any], file_names: List[str]) -> Dict[str, Any]:
        """Add documents to the knowledge base"""
        results = {
            "success": [],
            "errors": [],
            "total_chunks": 0
        }
        
        for file_data, filename in zip(files, file_names):
            try:
                # Extract text from file
                text, _ = extract_text(file_data, filename)
                if not text.strip():
                    results["errors"].append(f"No text extracted from {filename}")
                    continue
                
                # Split text into chunks
                chunks = self.text_splitter.split_text(text)
                
                # Create documents with metadata
                documents = []
                metadatas = []
                ids = []
                
                for i, chunk in enumerate(chunks):
                    doc_id = f"{filename}_{i}_{uuid.uuid4().hex[:8]}"
                    documents.append(chunk)
                    metadatas.append({
                        "filename": filename,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    })
                    ids.append(doc_id)
                
                # Add to ChromaDB
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                results["success"].append({
                    "filename": filename,
                    "chunks": len(chunks)
                })
                results["total_chunks"] += len(chunks)
                
            except Exception as e:
                results["errors"].append(f"Error processing {filename}: {str(e)}")
        
        return results
    
    def search_similar(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents in the knowledge base"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        "content": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 0
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching knowledge base: {e}")
            return []
    
    def get_knowledge_context(self, query: str, max_chunks: int = 10) -> str:
        """Get relevant context from knowledge base for a query"""
        similar_docs = self.search_similar(query, n_results=max_chunks)
        
        if not similar_docs:
            return ""
        
        context_parts = []
        for doc in similar_docs:
            filename = doc['metadata'].get('filename', 'Unknown')
            content = doc['content']
            context_parts.append(f"From {filename}:\n{content}\n")
        
        return "\n".join(context_parts)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection.name
            }
        except Exception as e:
            return {"error": str(e)}
    
    def clear_knowledge_base(self) -> bool:
        """Clear all documents from the knowledge base"""
        try:
            self.client.delete_collection("contracts_knowledge")
            self.collection = self.client.get_or_create_collection(
                name="contracts_knowledge",
                metadata={"description": "Contract and SOW knowledge base"}
            )
            return True
        except Exception as e:
            print(f"Error clearing knowledge base: {e}")
            return False

# Global RAG service instance
rag_service = RAGService()
