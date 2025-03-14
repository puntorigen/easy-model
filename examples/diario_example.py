"""
Example demonstrating the enhanced relationship handling in async-easy-model
using the RegistroDiario and EntradaDiario models from the original request.

This example shows how to:
1. Define the models with relationships
2. Create diary entries with relationships
3. Fetch diary entries with their related records
4. Simplify the code in the original example
"""

import asyncio
import sys
from pathlib import Path
import os

# Add the parent directory to sys.path to import the package
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Field, Relationship, Enum
from typing import List, Optional
from datetime import datetime, date
from enum import Enum as PyEnum
from async_easy_model import EasyModel, init_db, db_config

# Configure SQLite for the example
db_config.configure_sqlite("diario.db")

# Define models with relationships
class EstadoAnimo(str, PyEnum):
    """Enumeración para representar el estado de ánimo."""
    EXCELENTE = "excelente"
    BUENO = "bueno"
    NEUTRAL = "neutral"
    REGULAR = "regular"
    MALO = "malo"

class EntradaDiario(EasyModel, table=True):
    """
    Representa una entrada individual en el diario.
    """
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    titulo: str = Field(..., min_length=3, description="Título de la entrada")
    contenido: str = Field(..., min_length=10, description="Contenido de la entrada")
    estado_animo: str = Field(
        default="neutral",
        sa_column=Enum("excelente","bueno","neutral","regular","malo"),
        description="Estado de ánimo al momento de escribir"
    )
    fecha_creacion: datetime = Field(
        default_factory=datetime.now,
        description="Fecha y hora de creación",
        exclude=True  # No pedir al usuario
    )
    etiquetas: str = Field(
        description="Lista de etiquetas separadas por comas (opcional)"
    )
    registro_id: Optional[int] = Field(default=None, foreign_key="registrodiario.id")
    registro: Optional["RegistroDiario"] = Relationship(back_populates="entradas")

class RegistroDiario(EasyModel, table=True):
    """
    Representa el registro completo del diario, organizado por fecha.
    """
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    fecha: date = Field(
        default_factory=date.today,
        description="Fecha del registro"
    )
    entradas: List["EntradaDiario"] = Relationship(back_populates="registro")
    resumen_dia: Optional[str] = Field(
        None,
        description="Resumen opcional del día completo"
    )

async def run_example():
    """Run the example code demonstrating relationship features with the diary models."""
    print("Initializing database...")
    await init_db()
    
    # Create a diary record for today
    today = date.today()
    print(f"\nCreating a diary record for {today}...")
    
    # First, check if a record for today already exists
    registro = await RegistroDiario.get_by_attribute(fecha=today)
    
    if not registro:
        # Create a new diary record for today
        registro_data = {
            "fecha": today,
            "resumen_dia": "Un día productivo trabajando en mejoras de código."
        }
        registro = await RegistroDiario.insert(registro_data)
        print(f"Created new diary record for {registro.fecha}")
    else:
        print(f"Found existing diary record for {registro.fecha}")
    
    # Create a diary entry using the insert_with_related method
    print("\nCreating diary entries with the new relationship features...")
    
    # Method 1: Create entries separately
    entrada_data = {
        "titulo": "Mejoras en async-easy-model",
        "contenido": "Implementé nuevas funcionalidades para manejar relaciones en async-easy-model.",
        "estado_animo": "excelente",
        "etiquetas": "programación,python,orm",
        "registro_id": registro.id
    }
    entrada = await EntradaDiario.insert(entrada_data)
    print(f"Created diary entry: {entrada.titulo}")
    
    # Method 2: Create a diary record with entries in a single transaction
    print("\nCreating a diary record with entries in a single transaction...")
    tomorrow = date(today.year, today.month, today.day + 1)
    
    new_registro = await RegistroDiario.insert_with_related(
        data={
            "fecha": tomorrow,
            "resumen_dia": "Planificación para el día siguiente."
        },
        related_data={
            "entradas": [
                {
                    "titulo": "Tareas pendientes",
                    "contenido": "Completar la documentación del proyecto.",
                    "estado_animo": "bueno",
                    "etiquetas": "tareas,documentación"
                },
                {
                    "titulo": "Ideas nuevas",
                    "contenido": "Explorar nuevas funcionalidades para el proyecto.",
                    "estado_animo": "excelente",
                    "etiquetas": "ideas,innovación"
                }
            ]
        }
    )
    
    print(f"Created diary record for {new_registro.fecha} with {len(new_registro.entradas)} entries")
    
    # Fetch a diary record with its entries
    print("\nFetching a diary record with its entries...")
    registro_with_entries = await RegistroDiario.get_by_id(registro.id, include_relationships=True)
    print(f"Diary record for {registro_with_entries.fecha}")
    print(f"Summary: {registro_with_entries.resumen_dia}")
    print("Entries:")
    for entrada in registro_with_entries.entradas:
        print(f"- {entrada.titulo}: {entrada.contenido[:30]}...")
    
    # Convert to dictionary with relationships
    print("\nConverting to dictionary with relationships...")
    registro_dict = registro_with_entries.to_dict(include_relationships=True)
    print(f"Diary record dict for {registro_dict['fecha']}")
    print(f"Entries in dict: {len(registro_dict['entradas'])}")
    
    # Example of how this would simplify the original code
    print("\nExample of simplified code for the original use case:")
    print("""
    @ui.refreshable
    async def informe_del_dia(fecha="2025-02-27"):
        with ui.element("p"):
            ui.label("Informe del día").classes("text-h4 mb-4")
            
            # Get the diary record with entries in a single query
            dia = await RegistroDiario.get_by_attribute(
                fecha=fecha, 
                include_relationships=True
            )
            
            with ui.timeline(side="right", color="cyan"):
                if dia:
                    if dia.entradas:
                        for entrada in dia.entradas:
                            fechahora_formateada = entrada.fecha_creacion.strftime("%d %b, %Y %H:%M") 
                            ui.timeline_entry(
                                title=entrada.titulo, 
                                subtitle=fechahora_formateada, 
                                body=entrada.contenido
                            )
                    else:
                        ui.timeline_entry(subtitle="No hay entradas para esta fecha.")
                else:
                    ui.timeline_entry(subtitle="No hay registros para esta fecha.")
    """)

if __name__ == "__main__":
    asyncio.run(run_example())
