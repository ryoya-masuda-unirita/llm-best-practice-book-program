"""Chapter 3, Section 5: CQRS Knowledge Base Implementation."""

from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)
