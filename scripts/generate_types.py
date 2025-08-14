#!/usr/bin/env python3
"""Generate TypeScript types from Pydantic models"""

from pathlib import Path
from typing import get_type_hints, Union, Optional, get_args, get_origin
from datetime import datetime
from enum import Enum
import sys
# Ensure the backend directory is on sys.path so 'app' is importable


# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    # Import your Pydantic models from the actual location
    from backend.app.models.schemas import (
        # Domain schemas
        Location,
        LineItem,
        ReceiptDetails,
        AuditDecision,
        ProcessingResult,
        EvaluationRecord,
        
        # API schemas
        UserRead,
        UserCreate,
        UserUpdate,
        ReceiptRead,
        ReceiptResponse,
        ReceiptUpdate,
        ReceiptListResponse,
        AuditRuleBase,
        AuditRuleCreate,
        AuditRuleNLCreate,
        AuditRuleUpdate,
        AuditRuleRead,
        PromptTemplateBase,
        PromptTemplateCreate,
        PromptTemplateUpdate,
        PromptTemplateRead,
        EvaluationCreate,
        EvaluationSummary,
        EvaluationUpdate,
        CostAnalysisCreate,
        CostAnalysisRead,
        AuditRead,
        JobResponse,
        JobStatus
    )
    
    # Import enums
    from backend.app.models.enums import (
        PlanType,
        RuleType,
        ReceiptStatus,
        EvaluationStatus
    )
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Backend path: {backend_path}")
    print("\nMake sure your backend structure is:")
    print("backend/")
    print("├── app/")
    print("│   ├── models/")
    print("│   │   ├── __init__.py")
    print("│   │   ├── schemas.py")
    print("│   │   └── enums.py")
    sys.exit(1)

def python_type_to_ts(py_type, type_name: str = None):
    """Convert Python type to TypeScript type"""
    if py_type is None:
        return "any"
        
    type_map = {
        str: "string",
        int: "number",
        float: "number",
        bool: "boolean",
        datetime: "string",  # ISO string
        type(None): "null",
        dict: "Record<string, any>",
        list: "any[]",
    }
    
    # Get the origin type for generics
    origin = get_origin(py_type)
    
    # Handle Union types (including Optional)
    if origin is Union:
        args = get_args(py_type)
        types = [python_type_to_ts(t, type_name) for t in args if t != type(None)]
        if type(None) in args:
            return f"{' | '.join(types)} | null"
        return ' | '.join(types)
    
    # Handle List types
    if origin is list:
        args = get_args(py_type)
        if args:
            inner_type = python_type_to_ts(args[0], type_name)
            return f"{inner_type}[]"
        return "any[]"
    
    # Handle Dict types
    if origin is dict:
        args = get_args(py_type)
        if len(args) == 2:
            key_type = python_type_to_ts(args[0], type_name)
            value_type = python_type_to_ts(args[1], type_name)
            return f"Record<{key_type}, {value_type}>"
        return "Record<string, any>"
    
    # Handle specific enums
    if py_type == ReceiptStatus:
        return "ReceiptStatus"
    elif py_type == PlanType:
        return "PlanType"
    elif py_type == RuleType:
        return "RuleType"
    elif py_type == EvaluationStatus:
        return "EvaluationStatus"
    elif py_type == JobStatus:
        return "JobStatus"
    
    # Handle Pydantic models (nested references)
    if hasattr(py_type, '__fields__') or hasattr(py_type, 'model_fields'):
        return py_type.__name__
    
    # Handle Enum base class
    if isinstance(py_type, type) and issubclass(py_type, Enum):
        return ' | '.join([f'"{e.value}"' for e in py_type])
    
    return type_map.get(py_type, "any")

def generate_enum(enum_class, enum_name):
    """Generate TypeScript enum type"""
    values = ' | '.join([f'"{e.value}"' for e in enum_class])
    return f"export type {enum_name} = {values};"

def generate_interface(model_class, interface_name):
    """Generate TypeScript interface from Pydantic model"""
    lines = [f"export interface {interface_name} {{"]
    
    # Get all fields from the model
    if hasattr(model_class, 'model_fields'):
        # Pydantic v2
        for field_name, field_info in model_class.model_fields.items():
            ts_type = python_type_to_ts(field_info.annotation, field_name)
            optional = "?" if not field_info.is_required() else ""
            lines.append(f"  {field_name}{optional}: {ts_type};")
    elif hasattr(model_class, '__fields__'):
        # Pydantic v1
        for field_name, field_info in model_class.__fields__.items():
            ts_type = python_type_to_ts(field_info.type_, field_name)
            optional = "?" if not field_info.required else ""
            lines.append(f"  {field_name}{optional}: {ts_type};")
    
    lines.append("}")
    return "\n".join(lines)

def main():
    """Generate all TypeScript interfaces"""
    output_dir = Path(__file__).parent.parent / "shared" / "types"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate main types file
    types_content = []
    types_content.append("// Auto-generated from Pydantic models")
    types_content.append("// Do not edit manually")
    types_content.append("// Run 'pnpm generate:types' to regenerate")
    types_content.append("")
    
    # Generate enums first
    print("Generating enums...")
    enums = [
        (ReceiptStatus, "ReceiptStatus"),
        (PlanType, "PlanType"),
        (RuleType, "RuleType"),
        (EvaluationStatus, "EvaluationStatus"),
        (JobStatus, "JobStatus"),
    ]
    
    for enum_class, name in enums:
        try:
            types_content.append(generate_enum(enum_class, name))
            types_content.append("")
            print(f"  ✅ {name}")
        except Exception as e:
            print(f"  ⚠️  {name}: {e}")
    
    # Generate interfaces
    print("\nGenerating interfaces...")
    models = [
        # Domain models
        (Location, "Location"),
        (LineItem, "LineItem"),
        (ReceiptDetails, "ReceiptDetails"),
        (AuditDecision, "AuditDecision"),
        (ProcessingResult, "ProcessingResult"),
        (EvaluationRecord, "EvaluationRecord"),
        
        # User models
        (UserRead, "User"),
        (UserCreate, "UserCreate"),
        (UserUpdate, "UserUpdate"),
        
        # Receipt models
        (ReceiptRead, "Receipt"),
        (ReceiptResponse, "ReceiptResponse"),
        (ReceiptUpdate, "ReceiptUpdate"),
        (ReceiptListResponse, "ReceiptListResponse"),
        
        # Audit Rule models
        (AuditRuleBase, "AuditRuleBase"),
        (AuditRuleCreate, "AuditRuleCreate"),
        (AuditRuleNLCreate, "AuditRuleNLCreate"),
        (AuditRuleUpdate, "AuditRuleUpdate"),
        (AuditRuleRead, "AuditRule"),
        
        # Other models
        (PromptTemplateBase, "PromptTemplateBase"),
        (PromptTemplateCreate, "PromptTemplateCreate"),
        (PromptTemplateUpdate, "PromptTemplateUpdate"),
        (PromptTemplateRead, "PromptTemplate"),
        (EvaluationCreate, "EvaluationCreate"),
        (EvaluationSummary, "EvaluationSummary"),
        (EvaluationUpdate, "EvaluationUpdate"),
        (CostAnalysisCreate, "CostAnalysisCreate"),
        (CostAnalysisRead, "CostAnalysis"),
        (AuditRead, "Audit"),
        (JobResponse, "Job"),
    ]
    
    generated_count = 0
    for model, name in models:
        try:
            types_content.append(generate_interface(model, name))
            types_content.append("")
            generated_count += 1
            print(f"  ✅ {name}")
        except Exception as e:
            print(f"  ⚠️  {name}: {e}")
    
    # Write main types file
    with open(output_dir / "index.ts", "w") as f:
        f.write("\n".join(types_content))
    
    # Generate API types file
    api_types = []
    api_types.append("// API utility types")
    api_types.append("")
    api_types.append("export interface ApiResponse<T> {")
    api_types.append("  data: T;")
    api_types.append("  message?: string;")
    api_types.append("  errors?: string[];")
    api_types.append("}")
    api_types.append("")
    api_types.append("export interface PaginatedResponse<T> {")
    api_types.append("  items: T[];")
    api_types.append("  total: number;")
    api_types.append("  page: number;")
    api_types.append("  page_size: number;")
    api_types.append("  total_pages: number;")
    api_types.append("}")
    api_types.append("")
    api_types.append("export interface ApiError {")
    api_types.append("  detail: string;")
    api_types.append("  status_code: number;")
    api_types.append("  type?: string;")
    api_types.append("}")
    
    with open(output_dir / "api.ts", "w") as f:
        f.write("\n".join(api_types))
    
    print(f"\n✅ Generated {generated_count} TypeScript interfaces in {output_dir}")
    print(f"   Created: index.ts (main types) and api.ts (utility types)")

if __name__ == "__main__":
    main()