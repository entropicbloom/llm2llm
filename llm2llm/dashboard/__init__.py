"""Dashboard package for LLM2LLM analysis visualization."""

from .html_generator import generate_html, write_dashboard
from .data import load_all_analyses, infer_provider

__all__ = ["generate_html", "write_dashboard", "load_all_analyses", "infer_provider"]
