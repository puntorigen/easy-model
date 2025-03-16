"""
Visualization utilities for EasyModel models.

This module provides tools to visualize EasyModel database schemas,
including tables, fields, relationships, and automatically generated virtual fields.
"""

import inspect
import sys
from typing import Dict, List, Optional, Type, Set, Any, Union
from sqlmodel import SQLModel, Field
from sqlalchemy import inspect as sa_inspect

class ModelVisualizer:
    """
    Helper class for visualizing EasyModel database schemas.
    
    This class provides methods to generate visual representations of the database schema,
    including tables, fields, relationships, and automatically generated virtual fields.
    
    Attributes:
        model_registry (Dict[str, Type[SQLModel]]): Dictionary of registered models
    """
    
    def __init__(self):
        """Initialize the ModelVisualizer."""
        self.model_registry = {}
        self._load_registered_models()
    
    def _load_registered_models(self):
        """
        Load all registered EasyModel models.
        This should be called after init_db has been executed.
        """
        # First try to get models from auto_relationships registry
        try:
            from .auto_relationships import _model_registry
            if _model_registry:
                self.model_registry = _model_registry.copy()
                return
        except (ImportError, AttributeError):
            pass
            
        # Fallback: discover models from loaded modules
        for module_name, module in sys.modules.items():
            if hasattr(module, "__dict__"):
                for cls_name, cls in module.__dict__.items():
                    if (inspect.isclass(cls) and 
                        issubclass(cls, SQLModel) and 
                        cls != SQLModel and 
                        hasattr(cls, "__tablename__")):
                        self.model_registry[cls.__name__] = cls
    
    def _get_foreign_keys(self, model_class: Type[SQLModel]) -> Dict[str, str]:
        """
        Extract foreign key information from a model class.
        
        Args:
            model_class: The SQLModel class to extract foreign keys from.
            
        Returns:
            Dictionary mapping field names to their foreign key references.
        """
        foreign_keys = {}
        
        try:
            # Check model annotations and __fields__ for foreign keys
            if hasattr(model_class, "__annotations__"):
                for field_name, field_type in model_class.__annotations__.items():
                    if hasattr(model_class, field_name):
                        field_value = getattr(model_class, field_name)
                        if hasattr(field_value, "foreign_key"):
                            if field_value.foreign_key:
                                foreign_keys[field_name] = field_value.foreign_key
            
            # Check model attributes for Field instances with foreign_key
            for attr_name in dir(model_class):
                if attr_name.startswith("__") or attr_name in foreign_keys:
                    continue
                try:
                    attr_value = getattr(model_class, attr_name)
                    if hasattr(attr_value, "foreign_key"):
                        if attr_value.foreign_key:
                            foreign_keys[attr_name] = attr_value.foreign_key
                except (AttributeError, TypeError):
                    pass
            
            # Try to infer foreign keys from field names ending with _id
            if hasattr(model_class, "__fields__"):
                for field_name in model_class.__fields__:
                    if field_name.endswith("_id") and field_name not in foreign_keys:
                        related_name = field_name[:-3]  # Remove _id suffix
                        # Check if there's a model with this name
                        for model_name in self.model_registry:
                            if model_name.lower() == related_name.lower():
                                foreign_keys[field_name] = f"{model_name.lower()}.id"
                                break
        except Exception as e:
            # Log but don't re-raise to ensure visualization continues
            print(f"Warning: Error getting foreign keys for {model_class.__name__}: {str(e)}")
        
        return foreign_keys
    
    def _get_virtual_relationship_fields(self, model_class: Type[SQLModel]) -> Dict[str, Dict[str, Any]]:
        """
        Get virtual relationship fields that are automatically generated.
        
        Args:
            model_class: The SQLModel class to extract virtual relationship fields from.
            
        Returns:
            Dictionary of virtual relationship fields info.
        """
        virtual_fields = {}
        table_name = getattr(model_class, "__tablename__", model_class.__name__.lower())
        
        try:
            # Check for junction tables (tables with two foreign keys that form many-to-many)
            foreign_keys = self._get_foreign_keys(model_class)
            
            # Track models that have relations via this model's foreign keys
            related_models = set()
            
            # Determine if this is a junction table (has two foreign keys to different tables)
            is_junction_table = False
            if len(foreign_keys) >= 2:
                referenced_tables = set()
                for fk_target in foreign_keys.values():
                    if "." in fk_target:
                        referenced_tables.add(fk_target.split(".")[0])
                
                is_junction_table = len(referenced_tables) >= 2
            
            # For each foreign key, determine the virtual relationship field
            for field_name, fk_target in foreign_keys.items():
                if "." not in fk_target:
                    continue
                    
                target_table = fk_target.split(".")[0]
                
                # Find the related model class
                target_model = None
                for name, cls in self.model_registry.items():
                    cls_table_name = getattr(cls, "__tablename__", name.lower())
                    if cls_table_name.lower() == target_table.lower():
                        target_model = name
                        related_models.add(name)
                        break
                
                if not target_model:
                    continue
                
                # The relationship field is typically named without the _id suffix
                rel_name = field_name[:-3] if field_name.endswith("_id") else field_name
                
                # Skip if this looks like a duplicate relationship
                if rel_name in virtual_fields:
                    continue
                
                # Add the virtual relationship field (singular form - one instance)
                virtual_fields[rel_name] = {
                    "name": rel_name,
                    "type": target_model,
                    "is_list": False,  # One-to-one or many-to-one
                    "related_model": target_model,
                    "is_virtual": True,
                    "is_required": False  # Virtual fields are usually optional
                }
            
            # For junction tables, create the many-to-many virtual fields
            if is_junction_table and len(related_models) >= 2:
                # Don't add virtual fields to the junction table itself
                return virtual_fields
            
            # For each model, check if it's referenced in a junction table to create many-to-many virtuals
            for junction_name, junction_class in self.model_registry.items():
                junction_table_name = getattr(junction_class, "__tablename__", junction_name.lower())
                
                # Skip if this is not a potential junction table
                if junction_class == model_class:  # Skip self
                    continue
                
                junction_fks = self._get_foreign_keys(junction_class)
                if len(junction_fks) < 2:  # Not a potential junction
                    continue
                
                # Check if this model is referenced by the potential junction table
                this_model_referenced = False
                other_referenced_models = set()
                
                for fk_target in junction_fks.values():
                    if "." not in fk_target:
                        continue
                        
                    target_table = fk_target.split(".")[0]
                    
                    if target_table == table_name:
                        this_model_referenced = True
                    else:
                        # Find the model class for this target
                        for other_name, other_cls in self.model_registry.items():
                            other_table = getattr(other_cls, "__tablename__", other_name.lower())
                            if other_table == target_table:
                                other_referenced_models.add(other_name)
                                break
                
                # If this is a junction table connecting this model to others
                if this_model_referenced and other_referenced_models:
                    for other_model in other_referenced_models:
                        # Create a plural form of the model name for the relationship
                        # This is a very simple pluralization, might need to improve
                        other_model_lower = other_model.lower()
                        plural_name = f"{other_model_lower}s"
                        
                        # Add the many-to-many virtual field (plural form)
                        virtual_fields[plural_name] = {
                            "name": plural_name,
                            "type": f"List[{other_model}]",
                            "is_list": True,  # Many-to-many
                            "related_model": other_model,
                            "is_virtual": True,
                            "is_required": False
                        }
            
        except Exception as e:
            # Log but don't re-raise to ensure visualization continues
            print(f"Warning: Error getting virtual fields for {model_class.__name__}: {str(e)}")
        
        return virtual_fields
    
    def _get_field_information(self, model_class: Type[SQLModel]) -> Dict[str, Dict[str, Any]]:
        """
        Extract field information from a model class.
        
        Args:
            model_class: The SQLModel class to extract field information from.
            
        Returns:
            Dictionary of field information with field names as keys.
        """
        fields = {}
        
        try:
            # Make sure the 'id' field is always included
            fields["id"] = {
                "name": "id",
                "type": "int",
                "is_primary": True,
                "is_foreign_key": False,
                "foreign_key_reference": None,
                "is_virtual": False,
                "is_required": True
            }
            
            # Get standard database fields
            if hasattr(model_class, "__annotations__"):
                for field_name, field_type in model_class.__annotations__.items():
                    # Skip private fields
                    if field_name.startswith("_"):
                        continue
                    
                    # Get field type as string
                    type_str = getattr(field_type, "__name__", str(field_type))
                    
                    # Check if field is optional
                    is_optional = False
                    if hasattr(field_type, "__origin__"):
                        if field_type.__origin__ is Union:
                            args = getattr(field_type, "__args__", [])
                            if type(None) in args:
                                is_optional = True
                                # Simplify type for optional fields (remove Union and NoneType)
                                other_types = [arg for arg in args if arg is not type(None)]
                                if len(other_types) == 1:
                                    # If there's only one other type (common case like Optional[str])
                                    type_str = getattr(other_types[0], "__name__", str(other_types[0]))
                                else:
                                    # For more complex unions, just indicate it's a Union
                                    type_str = "Union"
                    
                    # Check if it's a primary key
                    is_primary = field_name == "id"
                    
                    # Store field information
                    fields[field_name] = {
                        "name": field_name,
                        "type": type_str,
                        "is_primary": is_primary,
                        "is_foreign_key": False,
                        "foreign_key_reference": None,
                        "is_virtual": False,
                        "is_required": not is_optional
                    }
            
            # Get foreign key information and update fields
            foreign_keys = self._get_foreign_keys(model_class)
            for field_name, fk_target in foreign_keys.items():
                if field_name in fields:
                    fields[field_name]["is_foreign_key"] = True
                    fields[field_name]["foreign_key_reference"] = fk_target
                else:
                    # Foreign key field wasn't in annotations, add it
                    fields[field_name] = {
                        "name": field_name,
                        "type": "int",  # Most foreign keys are integers
                        "is_primary": False,
                        "is_foreign_key": True,
                        "foreign_key_reference": fk_target,
                        "is_virtual": False,
                        "is_required": True  # Assume foreign keys are required by default
                    }
            
            # Get virtual relationship fields
            virtual_fields = self._get_virtual_relationship_fields(model_class)
            for field_name, field_info in virtual_fields.items():
                fields[field_name] = field_info
        
        except Exception as e:
            # Log but don't re-raise to ensure visualization continue
            print(f"Warning: Error processing fields for {model_class.__name__}: {str(e)}")
        
        return fields
    
    def _simplify_type_for_mermaid(self, type_str: str) -> str:
        """
        Simplify a Python type string for Mermaid ER diagram display.
        
        Args:
            type_str: Python type string to simplify
            
        Returns:
            A simplified type string suitable for Mermaid diagrams
        """
        # Remove common Python type prefixes
        simplified = type_str.replace("typing.", "").replace("__main__.", "")
        
        # Handle common container types
        if simplified.startswith("List["):
            inner_type = simplified[5:-1]  # Extract the type inside List[]
            return f"{inner_type}[]"
        
        # Handle other complex types that might confuse Mermaid
        if "[" in simplified or "Union" in simplified or "Optional" in simplified:
            # For complex types, just return a more generic type name
            if "str" in simplified:
                return "string"
            elif "int" in simplified or "float" in simplified:
                return "number"
            elif "bool" in simplified:
                return "boolean"
            elif "dict" in simplified or "Dict" in simplified:
                return "object"
            else:
                return "any"
        
        # Simple type mapping to more Mermaid-friendly types
        type_map = {
            "str": "string",
            "int": "number",
            "float": "number",
            "bool": "boolean",
            "dict": "object",
            "Dict": "object",
            "datetime": "date",
            "date": "date",
            "time": "time",
            "bytes": "binary",
            "bytearray": "binary"
        }
        
        return type_map.get(simplified, simplified)
    
    def generate_mermaid_er_diagram(self) -> str:
        """
        Generate a Mermaid ER diagram for all registered models.
        
        Returns:
            String containing Mermaid ER diagram markup.
        """
        if not self.model_registry:
            return "```mermaid\nerDiagram\n    %% No models found. Run init_db first.\n```"
        
        lines = ["```mermaid", "erDiagram"]
        
        # Keep track of rendered relationships to avoid duplicates
        rendered_relationships = set()
        processed_models = set()
        
        # Try to process all models, but continue even if some fail
        for model_name, model_class in self.model_registry.items():
            try:
                table_name = getattr(model_class, "__tablename__", model_name.lower())
                processed_models.add(model_name)
                
                # Add entity definition
                lines.append(f"    {table_name} {{")
                
                # Get fields for this model
                fields = self._get_field_information(model_class)
                
                # Add fields
                for field_name, field_info in fields.items():
                    # Format type
                    field_type = self._simplify_type_for_mermaid(str(field_info["type"]))
                    
                    # Add attributes like PK, FK
                    attrs = []
                    if field_info.get("is_primary", False):
                        attrs.append("PK")
                    if field_info.get("is_foreign_key", False):
                        attrs.append("FK")
                    
                    # Add indicator for virtual fields
                    if field_info.get("is_virtual", False):
                        attrs.append("virtual")
                    
                    # Format attributes string
                    attrs_str = f" {', '.join(attrs)}" if attrs else ""
                    
                    # Add required field indicator (asterisk)
                    field_name_formatted = f"*{field_name}" if field_info.get("is_required", True) else field_name
                    
                    # Add field
                    lines.append(f"        {field_type} {field_name_formatted}{attrs_str}")
                
                # Close entity definition
                lines.append("    }")
            
            except Exception as e:
                lines.append(f"    %% Error defining {model_name}: {str(e)}")
        
        # Add relationships between models
        for model_name, model_class in self.model_registry.items():
            try:
                if model_name not in processed_models:
                    continue
                    
                table_name = getattr(model_class, "__tablename__", model_name.lower())
                
                # Get fields for this model
                fields = self._get_field_information(model_class)
                
                # Add relationships based on foreign keys
                for field_name, field_info in fields.items():
                    if field_info.get("is_foreign_key", False) and field_info.get("foreign_key_reference"):
                        # Parse the foreign key reference to get the target table
                        fk_ref = field_info["foreign_key_reference"]
                        target_table = fk_ref.split(".")[0] if "." in fk_ref else fk_ref
                        
                        # Create relationship ID to avoid duplicates
                        rel_id = f"{table_name}_{target_table}_{field_name}"
                        if rel_id in rendered_relationships:
                            continue
                        
                        # Add the relationship
                        lines.append(f"    {table_name} ||--o{{ {target_table} : \"{field_name}\"")
                        rendered_relationships.add(rel_id)
                
                # Add many-to-many relationships
                # Check if this model might be a junction table
                if len(fields) >= 3:  # id + at least 2 foreign keys
                    foreign_key_fields = [f for f in fields.values() if f.get("is_foreign_key", False)]
                    
                    if len(foreign_key_fields) >= 2:
                        # This might be a junction table, try to render special M:N relationship
                        for i, fk1 in enumerate(foreign_key_fields):
                            for fk2 in foreign_key_fields[i+1:]:
                                # Skip if either field doesn't have a foreign key reference
                                if not fk1.get("foreign_key_reference") or not fk2.get("foreign_key_reference"):
                                    continue
                                    
                                # Get the target tables
                                target1 = fk1["foreign_key_reference"].split(".")[0]
                                target2 = fk2["foreign_key_reference"].split(".")[0]
                                
                                # Skip self-references or duplicates
                                if target1 == target2:
                                    continue
                                    
                                # Create relationship IDs
                                rel_id1 = f"{target1}_{target2}_m2m"
                                rel_id2 = f"{target2}_{target1}_m2m"
                                
                                if rel_id1 in rendered_relationships or rel_id2 in rendered_relationships:
                                    continue
                                    
                                # Add the many-to-many relationship directly between the end entities
                                lines.append(f"    {target1} }}o--o{{ {target2} : \"many-to-many\"")
                                rendered_relationships.add(rel_id1)
            
            except Exception as e:
                lines.append(f"    %% Error processing relationships for {model_name}: {str(e)}")
        
        lines.append("```")
        
        return "\n".join(lines)
