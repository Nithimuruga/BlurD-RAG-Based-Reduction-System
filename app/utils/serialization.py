import numpy as np
from typing import Any, Dict, List, Union
import sys
import inspect

def convert_numpy_types(obj: Any) -> Any:
    """
    Convert numpy data types to Python native types for JSON serialization.
    Works recursively on dictionaries, lists, and individual values.
    Also converts custom classes like ProcessedDocument and TextSegment.
    
    Args:
        obj: The object to convert (can be a dict, list, or individual value)
        
    Returns:
        The object with numpy types and custom objects converted to Python native types
    """
    # Handle ProcessedDocument class
    if obj.__class__.__name__ == 'ProcessedDocument':
        return {
            'original_text': convert_numpy_types(obj.original_text),
            'processed_text': convert_numpy_types(obj.processed_text),
            'segments': convert_numpy_types(obj.segments),
            'metadata': convert_numpy_types(obj.metadata),
            # Convert the character map (keys are strings in MongoDB)
            'character_map': {str(k): v for k, v in convert_numpy_types(obj.character_map).items()},
            '_type': 'ProcessedDocument'  # Add type information for possible reconstitution
        }
    
    # Handle TextSegment class
    if obj.__class__.__name__ == 'TextSegment':
        return {
            'text': obj.text,
            'start': obj.start,
            'end': obj.end,
            'metadata': convert_numpy_types(obj.metadata),
            '_type': 'TextSegment'  # Add type information
        }
    
    # Handle dictionaries
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    
    # Handle lists and tuples
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    
    # Handle numpy scalars (convert to Python native types)
    elif isinstance(obj, np.number):
        return obj.item()  # Converts numpy type to equivalent Python type
    
    # Handle numpy arrays
    elif isinstance(obj, np.ndarray):
        return obj.tolist()  # Convert numpy array to list
    
    # Handle any other dataclass or object with __dict__ attribute
    elif hasattr(obj, '__dict__') and not callable(obj):
        try:
            # Convert object to dictionary
            return {
                **{k: convert_numpy_types(v) for k, v in obj.__dict__.items()},
                '_type': obj.__class__.__name__  # Add type information
            }
        except:
            pass
    
    # Return unchanged if not a numpy type or custom object
    return obj