from crewai import Crew, Task, Process
from agents.data_extractor import DataExtractorAgent
from agents.data_processor import DataProcessorAgent
from agents.query_handler import QueryHandlerAgent
from agents.pdf_generator import PDFGeneratorAgent
from agents.search_indexer import SearchIndexerAgent
from core.glpi import GLPIClient
from core.config import settings
from typing import Dict
from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import json

app = FastAPI()

# Initialize GLPI client OUTSIDE the function
glpi_client = GLPIClient()

# Initialize agents, passing glpi_client to DataExtractorAgent.
#data_extractor_agent = DataExtractorAgent(glpi_client=glpi_client, # Pass as keyword argument
#    role='Data Extractor', # Redundant here, but for clarity
#    goal='Retrieve and validate raw data from GLPI',
#    backstory="""Expert in extracting data from various sources,
#    especially GLPI. Resilient to API issues and data inconsistencies.""",
#    verbose=True,
#    allow_delegation=False
#    ) # Use the simpler Agent constructor
data_extractor_agent = DataExtractorAgent(glpi_client=glpi_client)
data_processor_agent = DataProcessorAgent()
query_handler_agent = QueryHandlerAgent()
pdf_generator_agent = PDFGeneratorAgent()
search_indexer_agent = SearchIndexerAgent()


def run_autopdf(incident_id: int, update_solution: bool = False) -> str:
    """Runs the AutoPDF workflow for a given incident ID."""

    extract_incident_task = Task(
        description=f"Extract details for GLPI incident ID {incident_id}",
        agent=data_extractor_agent,
        expected_output="Raw data of the incident",
    )
    extract_solution_task = Task(
        description=f"Extract solution for GLPI incident ID {incident_id}",
        agent=data_extractor_agent,
        expected_output="Raw solution data",
        context=[extract_incident_task],
    )
    extract_tasks_task = Task(
        description=f"Extract tasks for GLPI incident ID {incident_id}",
        agent=data_extractor_agent,
        expected_output="Raw tasks data",
        context=[extract_incident_task],
    )
    document_id = 12345  # TODO: Get this dynamically from GLPI
    extract_document_task = Task(
        description=f"Extract content of document ID {document_id}",
        agent=data_extractor_agent,
        expected_output="Raw document content",
        context=[],
    )
    process_data_task = Task(
        description="Process the extracted data from GLPI",
        agent=data_processor_agent,
        expected_output="Cleaned and structured data",
        context=[
            extract_incident_task,
            extract_document_task,
            extract_solution_task,
            extract_tasks_task,
        ],
    )
    generate_content_task = Task(
        description="Generate report content using RAG",
        agent=query_handler_agent,
        expected_output="Generated content for the report",
        context=[process_data_task],
    )
    create_pdf_task = Task(
        description="Create a PDF report",
        agent=pdf_generator_agent,
        expected_output="PDF file as bytes.",
        context=[generate_content_task],
    )
    index_pdf_task = Task(
        description="Store PDF and index",
        agent=search_indexer_agent,
        expected_output="Confirmation message",
        context=[create_pdf_task, process_data_task],
    )

    crew = Crew(
        agents=[
            data_extractor_agent,
            data_processor_agent,
            query_handler_agent,
            pdf_generator_agent,
            search_indexer_agent,
        ],
        tasks=[
            extract_incident_task,
            extract_solution_task,
            extract_tasks_task,
            extract_document_task,
            process_data_task,
            generate_content_task,
            create_pdf_task,
            index_pdf_task,
        ],
        process
