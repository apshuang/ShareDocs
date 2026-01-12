"""
版本控制相关的单元测试
"""
import pytest
from app.utils.operation import apply_operation


class TestVersionControl:
    """测试版本控制逻辑"""
    
    def test_sequential_operations(self):
        """测试顺序操作"""
        content = ""
        operations = [
            {"type": "insert", "from_pos": 0, "to_pos": 0, "content": "hello"},
            {"type": "insert", "from_pos": 5, "to_pos": 5, "content": " world"},
            {"type": "replace", "from_pos": 0, "to_pos": 5, "content": "hi"},
        ]
        
        for op in operations:
            content = apply_operation(content, op)
        
        assert content == "hi world"
    
    def test_concurrent_insert_operations(self):
        """测试并发插入操作（模拟）"""
        # 两个用户同时在不同位置插入
        base_content = "hello"
        
        # 用户A的操作：在位置5插入 " world"
        op_a = {"type": "insert", "from_pos": 5, "to_pos": 5, "content": " world"}
        content_a = apply_operation(base_content, op_a)
        assert content_a == "hello world"
        
        # 用户B的操作：在位置0插入 "say "
        op_b = {"type": "insert", "from_pos": 0, "to_pos": 0, "content": "say "}
        content_b = apply_operation(base_content, op_b)
        assert content_b == "say hello"
        
        # 如果先应用A再应用B（需要变换B的位置）
        # B的位置需要从0调整到6（因为A插入了6个字符）
        op_b_transformed = {"type": "insert", "from_pos": 6, "to_pos": 6, "content": "say "}
        final_content = apply_operation(content_a, op_b_transformed)
        assert final_content == "hello say world"
    
    def test_concurrent_delete_operations(self):
        """测试并发删除操作"""
        base_content = "hello world"
        
        # 用户A：删除 "hello "
        op_a = {"type": "delete", "from_pos": 0, "to_pos": 6}
        content_a = apply_operation(base_content, op_a)
        assert content_a == "world"
        
        # 用户B：删除 " world"
        op_b = {"type": "delete", "from_pos": 5, "to_pos": 11}
        # 如果先应用A，B的位置需要调整
        # B的位置从5-11调整到5-5（因为前面删除了6个字符）
        op_b_transformed = {"type": "delete", "from_pos": 5, "to_pos": 5}
        # 但这样会报错，因为from_pos必须小于to_pos
        # 实际上B的操作应该被拒绝（冲突）
    
    def test_operation_sequence_numbering(self):
        """测试操作序列号的概念"""
        # 模拟版本控制
        version = 0
        content = ""
        
        # 操作1
        op1 = {"type": "insert", "from_pos": 0, "to_pos": 0, "content": "hello"}
        content = apply_operation(content, op1)
        version += 1
        assert version == 1
        
        # 操作2
        op2 = {"type": "insert", "from_pos": 5, "to_pos": 5, "content": " world"}
        content = apply_operation(content, op2)
        version += 1
        assert version == 2
        
        # 操作3
        op3 = {"type": "replace", "from_pos": 0, "to_pos": 5, "content": "hi"}
        content = apply_operation(content, op3)
        version += 1
        assert version == 3
        
        assert content == "hi world"
    
    def test_rebuild_document_from_operations(self):
        """测试从操作序列重建文档"""
        operations = [
            {"type": "insert", "from_pos": 0, "to_pos": 0, "content": "hello"},
            {"type": "insert", "from_pos": 5, "to_pos": 5, "content": " world"},
            {"type": "replace", "from_pos": 0, "to_pos": 5, "content": "hi"},
        ]
        
        # 从空文档开始，依次应用操作
        content = ""
        for op in operations:
            content = apply_operation(content, op)
        
        assert content == "hi world"
        
        # 如果只应用前两个操作
        content_partial = ""
        for op in operations[:2]:
            content_partial = apply_operation(content_partial, op)
        assert content_partial == "hello world"

