from typing import Dict, Any


def apply_insert(content: str, from_pos: int, to_pos: int, insert_content: str) -> str:
    if from_pos != to_pos:
        raise ValueError("insert 操作的 from_pos 和 to_pos 必须相等")
    if from_pos > len(content):
        raise ValueError(f"插入位置 {from_pos} 超出文档长度 {len(content)}")
    return content[:from_pos] + insert_content + content[from_pos:]


def apply_delete(content: str, from_pos: int, to_pos: int) -> str:
    if from_pos >= to_pos:
        raise ValueError("delete 操作的 from_pos 必须小于 to_pos")
    if to_pos > len(content):
        raise ValueError(f"删除位置 {to_pos} 超出文档长度 {len(content)}")
    return content[:from_pos] + content[to_pos:]


def apply_format(content: str, from_pos: int, to_pos: int, marks: Dict[str, Any]) -> str:
    if from_pos >= to_pos:
        raise ValueError("format 操作的 from_pos 必须小于 to_pos")
    if to_pos > len(content):
        raise ValueError(f"格式化位置 {to_pos} 超出文档长度 {len(content)}")
    
    selected_text = content[from_pos:to_pos]
    
    if "bold" in marks and marks["bold"]:
        selected_text = f"**{selected_text}**"
    elif "bold" in marks and not marks["bold"]:
        selected_text = selected_text.replace("**", "")
    
    if "italic" in marks and marks["italic"]:
        selected_text = f"*{selected_text}*"
    elif "italic" in marks and not marks["italic"]:
        selected_text = selected_text.replace("*", "")
    
    if "code" in marks and marks["code"]:
        selected_text = f"`{selected_text}`"
    elif "code" in marks and not marks["code"]:
        selected_text = selected_text.replace("`", "")
    
    return content[:from_pos] + selected_text + content[to_pos:]


def apply_replace(content: str, from_pos: int, to_pos: int, replace_content: str) -> str:
    if from_pos >= to_pos:
        raise ValueError("replace 操作的 from_pos 必须小于 to_pos")
    if to_pos > len(content):
        raise ValueError(f"替换位置 {to_pos} 超出文档长度 {len(content)}")
    return content[:from_pos] + replace_content + content[to_pos:]


def apply_operation(content: str, operation: Dict[str, Any]) -> str:
    op_type = operation["type"]
    from_pos = operation["from_pos"]
    to_pos = operation["to_pos"]
    
    if op_type == "insert":
        if "content" not in operation:
            raise ValueError("insert 操作必须提供 content")
        return apply_insert(content, from_pos, to_pos, operation["content"])
    
    elif op_type == "delete":
        return apply_delete(content, from_pos, to_pos)
    
    elif op_type == "format":
        if "marks" not in operation:
            raise ValueError("format 操作必须提供 marks")
        return apply_format(content, from_pos, to_pos, operation["marks"])
    
    elif op_type == "replace":
        if "content" not in operation:
            raise ValueError("replace 操作必须提供 content")
        return apply_replace(content, from_pos, to_pos, operation["content"])
    
    else:
        raise ValueError(f"不支持的操作类型: {op_type}")

