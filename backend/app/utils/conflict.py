from typing import Dict, Any, List, Tuple, Optional


def ranges_overlap(range1: Tuple[int, int], range2: Tuple[int, int]) -> bool:
    start1, end1 = range1
    start2, end2 = range2
    return not (end1 <= start2 or end2 <= start1)


def get_operation_range(operation: Dict[str, Any]) -> Optional[Tuple[int, int]]:
    op_type = operation.get("type")
    if op_type in ["delete", "replace", "format"]:
        from_pos = operation.get("from_pos", 0)
        to_pos = operation.get("to_pos", 0)
        return (from_pos, to_pos)
    return None


def adjust_position_for_operations(
    position: int,
    operations: List[Dict[str, Any]],
    operation_type: str
) -> int:
    adjusted_pos = position
    
    for op in operations:
        op_type = op.get("type")
        op_from = op.get("from_pos", 0)
        op_to = op.get("to_pos", 0)
        
        if op_type == "insert":
            if op_from <= adjusted_pos:
                adjusted_pos += len(op.get("content", ""))
        
        elif op_type == "delete":
            if op_to <= adjusted_pos:
                adjusted_pos -= (op_to - op_from)
            elif op_from < adjusted_pos < op_to:
                adjusted_pos = op_from
        
        elif op_type == "replace":
            old_length = op_to - op_from
            new_length = len(op.get("content", ""))
            diff = new_length - old_length
            
            if op_to <= adjusted_pos:
                adjusted_pos += diff
            elif op_from < adjusted_pos < op_to:
                adjusted_pos = op_from + new_length
    
    return adjusted_pos


def check_operation_conflict(
    current_operation: Dict[str, Any],
    history_operations: List[Dict[str, Any]]
) -> Tuple[bool, Optional[str]]:
    current_type = current_operation.get("type")
    
    if current_type == "insert":
        return False, None
    
    if current_type == "format":
        return False, None
    
    current_range = get_operation_range(current_operation)
    if not current_range:
        return False, None
    
    for hist_op in history_operations:
        hist_type = hist_op.get("type")
        
        if hist_type in ["insert", "format"]:
            continue
        
        if hist_type not in ["delete", "replace"]:
            continue
        
        hist_range = get_operation_range(hist_op)
        if not hist_range:
            continue
        
        overlap = ranges_overlap(current_range, hist_range)
        
        if overlap:
            if hist_type == "delete":
                if current_type == "delete":
                    return True, f"操作冲突：尝试删除的文本段已被删除（位置 {hist_range[0]}-{hist_range[1]}）"
                elif current_type == "replace":
                    return True, f"操作冲突：尝试替换的文本段已被删除（位置 {hist_range[0]}-{hist_range[1]}）"
            elif hist_type == "replace":
                if current_type == "delete":
                    return True, f"操作冲突：尝试删除的文本段已被替换（位置 {hist_range[0]}-{hist_range[1]}）"
                elif current_type == "replace":
                    return True, f"操作冲突：尝试替换的文本段已被替换（位置 {hist_range[0]}-{hist_range[1]}）"
    
    return False, None


def transform_operation_for_conflict_resolution(
    operation: Dict[str, Any],
    history_operations: List[Dict[str, Any]],
    current_content_length: int
) -> Dict[str, Any]:
    op_type = operation.get("type")
    op_from = operation.get("from_pos", 0)
    op_to = operation.get("to_pos", 0)
    
    transformed_op = operation.copy()
    
    if op_type == "insert":
        adjusted_from = adjust_position_for_operations(op_from, history_operations, op_type)
        if adjusted_from > current_content_length:
            adjusted_from = current_content_length
        transformed_op["from_pos"] = adjusted_from
        transformed_op["to_pos"] = adjusted_from
    
    elif op_type in ["delete", "replace"]:
        adjusted_from = adjust_position_for_operations(op_from, history_operations, op_type)
        adjusted_to = adjust_position_for_operations(op_to, history_operations, op_type)
        
        if adjusted_from < 0:
            adjusted_from = 0
        if adjusted_to < adjusted_from:
            adjusted_to = adjusted_from
        if adjusted_to > current_content_length:
            adjusted_to = current_content_length
        
        transformed_op["from_pos"] = adjusted_from
        transformed_op["to_pos"] = adjusted_to
    
    elif op_type == "format":
        adjusted_from = adjust_position_for_operations(op_from, history_operations, op_type)
        adjusted_to = adjust_position_for_operations(op_to, history_operations, op_type)
        
        if adjusted_from < 0:
            adjusted_from = 0
        if adjusted_to < adjusted_from:
            adjusted_to = adjusted_from
        if adjusted_to > current_content_length:
            adjusted_to = current_content_length
        
        transformed_op["from_pos"] = adjusted_from
        transformed_op["to_pos"] = adjusted_to
    
    return transformed_op

