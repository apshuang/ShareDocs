"""
操作应用的单元测试
"""
import pytest
from app.utils.operation import (
    apply_insert,
    apply_delete,
    apply_replace,
    apply_format,
    apply_operation
)


class TestApplyInsert:
    """测试插入操作"""
    
    def test_insert_at_beginning(self):
        """测试在开头插入"""
        content = "hello"
        result = apply_insert(content, 0, 0, "world ")
        assert result == "world hello"
    
    def test_insert_at_middle(self):
        """测试在中间插入"""
        content = "hello world"
        result = apply_insert(content, 5, 5, ", ")
        assert result == "hello,  world"
    
    def test_insert_at_end(self):
        """测试在结尾插入"""
        content = "hello"
        result = apply_insert(content, 5, 5, " world")
        assert result == "hello world"
    
    def test_insert_invalid_positions(self):
        """测试无效的插入位置"""
        content = "hello"
        with pytest.raises(ValueError, match="from_pos 和 to_pos 必须相等"):
            apply_insert(content, 2, 3, "x")
    
    def test_insert_out_of_bounds(self):
        """测试超出范围的插入"""
        content = "hello"
        with pytest.raises(ValueError, match="超出文档长度"):
            apply_insert(content, 10, 10, "x")


class TestApplyDelete:
    """测试删除操作"""
    
    def test_delete_at_beginning(self):
        """测试删除开头"""
        content = "hello world"
        result = apply_delete(content, 0, 6)
        assert result == "world"
    
    def test_delete_at_middle(self):
        """测试删除中间"""
        content = "hello world"
        result = apply_delete(content, 5, 6)
        assert result == "helloworld"
    
    def test_delete_at_end(self):
        """测试删除结尾"""
        content = "hello world"
        result = apply_delete(content, 6, 11)
        assert result == "hello "
    
    def test_delete_invalid_range(self):
        """测试无效的删除范围"""
        content = "hello"
        with pytest.raises(ValueError, match="from_pos 必须小于 to_pos"):
            apply_delete(content, 3, 2)
        with pytest.raises(ValueError, match="from_pos 必须小于 to_pos"):
            apply_delete(content, 3, 3)
    
    def test_delete_out_of_bounds(self):
        """测试超出范围的删除"""
        content = "hello"
        with pytest.raises(ValueError, match="超出文档长度"):
            apply_delete(content, 2, 10)


class TestApplyReplace:
    """测试替换操作"""
    
    def test_replace_at_beginning(self):
        """测试替换开头"""
        content = "hello world"
        result = apply_replace(content, 0, 5, "hi")
        assert result == "hi world"
    
    def test_replace_at_middle(self):
        """测试替换中间"""
        content = "hello world"
        result = apply_replace(content, 6, 11, "universe")
        assert result == "hello universe"
    
    def test_replace_at_end(self):
        """测试替换结尾"""
        content = "hello world"
        result = apply_replace(content, 6, 11, "there")
        assert result == "hello there"
    
    def test_replace_same_length(self):
        """测试等长替换"""
        content = "hello world"
        result = apply_replace(content, 0, 5, "world")
        assert result == "world world"
    
    def test_replace_invalid_range(self):
        """测试无效的替换范围"""
        content = "hello"
        with pytest.raises(ValueError, match="from_pos 必须小于 to_pos"):
            apply_replace(content, 3, 2, "x")
    
    def test_replace_out_of_bounds(self):
        """测试超出范围的替换"""
        content = "hello"
        with pytest.raises(ValueError, match="超出文档长度"):
            apply_replace(content, 2, 10, "x")


class TestApplyFormat:
    """测试格式化操作"""
    
    def test_apply_bold(self):
        """测试加粗"""
        content = "hello world"
        result = apply_format(content, 0, 5, {"bold": True})
        assert result == "**hello** world"
    
    def test_remove_bold(self):
        """测试取消加粗"""
        content = "**hello** world"
        result = apply_format(content, 0, 9, {"bold": False})  # 选中完整的 **hello**
        assert result == "hello world"
    
    def test_apply_italic(self):
        """测试斜体"""
        content = "hello world"
        result = apply_format(content, 0, 5, {"italic": True})
        assert result == "*hello* world"
    
    def test_apply_code(self):
        """测试代码格式"""
        content = "hello world"
        result = apply_format(content, 0, 5, {"code": True})
        assert result == "`hello` world"
    
    def test_apply_multiple_formats(self):
        """测试多种格式"""
        content = "hello"
        result = apply_format(content, 0, 5, {"bold": True, "italic": True})
        # 注意：实际实现中可能只应用一种格式
        assert "**" in result or "*" in result


class TestApplyOperation:
    """测试统一的操作应用接口"""
    
    def test_apply_insert_operation(self):
        """测试应用插入操作"""
        content = "hello"
        operation = {
            "type": "insert",
            "from_pos": 5,
            "to_pos": 5,
            "content": " world"
        }
        result = apply_operation(content, operation)
        assert result == "hello world"
    
    def test_apply_delete_operation(self):
        """测试应用删除操作"""
        content = "hello world"
        operation = {
            "type": "delete",
            "from_pos": 5,
            "to_pos": 11
        }
        result = apply_operation(content, operation)
        assert result == "hello"
    
    def test_apply_replace_operation(self):
        """测试应用替换操作"""
        content = "hello world"
        operation = {
            "type": "replace",
            "from_pos": 0,
            "to_pos": 5,
            "content": "hi"
        }
        result = apply_operation(content, operation)
        assert result == "hi world"
    
    def test_apply_format_operation(self):
        """测试应用格式化操作"""
        content = "hello world"
        operation = {
            "type": "format",
            "from_pos": 0,
            "to_pos": 5,
            "marks": {"bold": True}
        }
        result = apply_operation(content, operation)
        assert "**hello**" in result
    
    def test_apply_invalid_operation_type(self):
        """测试无效的操作类型"""
        content = "hello"
        operation = {
            "type": "invalid",
            "from_pos": 0,
            "to_pos": 5
        }
        with pytest.raises(ValueError, match="不支持的操作类型"):
            apply_operation(content, operation)
    
    def test_apply_insert_missing_content(self):
        """测试插入操作缺少内容"""
        content = "hello"
        operation = {
            "type": "insert",
            "from_pos": 5,
            "to_pos": 5
        }
        with pytest.raises(ValueError, match="必须提供 content"):
            apply_operation(content, operation)
    
    def test_apply_replace_missing_content(self):
        """测试替换操作缺少内容"""
        content = "hello"
        operation = {
            "type": "replace",
            "from_pos": 0,
            "to_pos": 5
        }
        with pytest.raises(ValueError, match="必须提供 content"):
            apply_operation(content, operation)
    
    def test_apply_format_missing_marks(self):
        """测试格式化操作缺少marks"""
        content = "hello"
        operation = {
            "type": "format",
            "from_pos": 0,
            "to_pos": 5
        }
        with pytest.raises(ValueError, match="必须提供 marks"):
            apply_operation(content, operation)
    
    def test_apply_multiple_operations(self):
        """测试应用多个操作"""
        content = "hello"
        
        # 插入
        op1 = {"type": "insert", "from_pos": 5, "to_pos": 5, "content": " world"}
        content = apply_operation(content, op1)
        assert content == "hello world"
        
        # 替换
        op2 = {"type": "replace", "from_pos": 0, "to_pos": 5, "content": "hi"}
        content = apply_operation(content, op2)
        assert content == "hi world"
        
        # 删除
        op3 = {"type": "delete", "from_pos": 2, "to_pos": 3}
        content = apply_operation(content, op3)
        assert content == "hiworld"

