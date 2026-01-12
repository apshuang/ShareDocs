"""
冲突检测和操作变换的单元测试
"""
import pytest
from app.utils.conflict import (
    ranges_overlap,
    get_operation_range,
    adjust_position_for_operations,
    check_operation_conflict,
    transform_operation_for_conflict_resolution
)


class TestRangesOverlap:
    """测试范围重叠检测"""
    
    def test_overlapping_ranges(self):
        """测试重叠的范围"""
        assert ranges_overlap((10, 20), (15, 25)) == True
        assert ranges_overlap((15, 25), (10, 20)) == True
        assert ranges_overlap((10, 20), (10, 20)) == True
        assert ranges_overlap((10, 20), (15, 18)) == True
    
    def test_non_overlapping_ranges(self):
        """测试不重叠的范围"""
        assert ranges_overlap((10, 20), (25, 30)) == False
        assert ranges_overlap((25, 30), (10, 20)) == False
        assert ranges_overlap((10, 20), (20, 30)) == False
    
    def test_adjacent_ranges(self):
        """测试相邻的范围"""
        assert ranges_overlap((10, 20), (20, 30)) == False


class TestGetOperationRange:
    """测试获取操作范围"""
    
    def test_delete_operation_range(self):
        """测试删除操作的范围"""
        op = {"type": "delete", "from_pos": 10, "to_pos": 20}
        assert get_operation_range(op) == (10, 20)
    
    def test_replace_operation_range(self):
        """测试替换操作的范围"""
        op = {"type": "replace", "from_pos": 10, "to_pos": 20, "content": "new"}
        assert get_operation_range(op) == (10, 20)
    
    def test_insert_operation_range(self):
        """测试插入操作的范围（应该返回None）"""
        op = {"type": "insert", "from_pos": 10, "to_pos": 10, "content": "text"}
        assert get_operation_range(op) is None
    
    def test_format_operation_range(self):
        """测试格式化操作的范围（应该返回None）"""
        op = {"type": "format", "from_pos": 10, "to_pos": 20, "marks": {}}
        assert get_operation_range(op) is None


class TestAdjustPositionForOperations:
    """测试位置调整"""
    
    def test_adjust_for_insert_before(self):
        """测试插入操作在位置之前"""
        operations = [
            {"type": "insert", "from_pos": 5, "to_pos": 5, "content": "abc"}
        ]
        result = adjust_position_for_operations(10, operations, "insert")
        assert result == 13  # 10 + 3
    
    def test_adjust_for_insert_after(self):
        """测试插入操作在位置之后"""
        operations = [
            {"type": "insert", "from_pos": 15, "to_pos": 15, "content": "abc"}
        ]
        result = adjust_position_for_operations(10, operations, "insert")
        assert result == 10  # 位置不变
    
    def test_adjust_for_delete_before(self):
        """测试删除操作在位置之前"""
        operations = [
            {"type": "delete", "from_pos": 5, "to_pos": 8}
        ]
        result = adjust_position_for_operations(10, operations, "delete")
        assert result == 7  # 10 - 3
    
    def test_adjust_for_delete_after(self):
        """测试删除操作在位置之后"""
        operations = [
            {"type": "delete", "from_pos": 15, "to_pos": 18}
        ]
        result = adjust_position_for_operations(10, operations, "delete")
        assert result == 10  # 位置不变
    
    def test_adjust_for_delete_overlapping(self):
        """测试删除操作包含位置"""
        operations = [
            {"type": "delete", "from_pos": 5, "to_pos": 15}
        ]
        result = adjust_position_for_operations(10, operations, "delete")
        assert result == 5  # 调整到删除起始位置
    
    def test_adjust_for_replace_before(self):
        """测试替换操作在位置之前（长度增加）"""
        operations = [
            {"type": "replace", "from_pos": 5, "to_pos": 8, "content": "abcdef"}
        ]
        result = adjust_position_for_operations(10, operations, "replace")
        assert result == 13  # 10 + (6 - 3) = 13
    
    def test_adjust_for_replace_before_shorter(self):
        """测试替换操作在位置之前（长度减少）"""
        operations = [
            {"type": "replace", "from_pos": 5, "to_pos": 8, "content": "a"}
        ]
        result = adjust_position_for_operations(10, operations, "replace")
        assert result == 8  # 10 + (1 - 3) = 8
    
    def test_adjust_for_replace_overlapping(self):
        """测试替换操作包含位置"""
        operations = [
            {"type": "replace", "from_pos": 5, "to_pos": 15, "content": "new"}
        ]
        result = adjust_position_for_operations(10, operations, "replace")
        assert result == 8  # 5 + 3
    
    def test_adjust_for_multiple_operations(self):
        """测试多个操作的位置调整"""
        operations = [
            {"type": "insert", "from_pos": 5, "to_pos": 5, "content": "abc"},
            {"type": "delete", "from_pos": 10, "to_pos": 13},
            {"type": "replace", "from_pos": 15, "to_pos": 18, "content": "xyz"}
        ]
        result = adjust_position_for_operations(20, operations, "insert")
        # 初始位置：20
        # 操作1：insert at 5 (+3) -> 23
        # 操作2：delete 10-13 (-3) -> 20
        # 操作3：replace 15-18 (diff=0) -> 20
        assert result == 20


class TestCheckOperationConflict:
    """测试冲突检测"""
    
    def test_insert_no_conflict(self):
        """测试插入操作不冲突"""
        current_op = {"type": "insert", "from_pos": 10, "to_pos": 10, "content": "text"}
        history_ops = [
            {"type": "delete", "from_pos": 5, "to_pos": 8}
        ]
        has_conflict, message = check_operation_conflict(current_op, history_ops)
        assert has_conflict == False
    
    def test_delete_vs_delete_conflict(self):
        """测试删除与删除冲突"""
        current_op = {"type": "delete", "from_pos": 10, "to_pos": 15}
        history_ops = [
            {"type": "delete", "from_pos": 12, "to_pos": 18}
        ]
        has_conflict, message = check_operation_conflict(current_op, history_ops)
        assert has_conflict == True
        assert "已被删除" in message
    
    def test_replace_vs_delete_conflict(self):
        """测试替换与删除冲突"""
        current_op = {"type": "replace", "from_pos": 10, "to_pos": 15, "content": "new"}
        history_ops = [
            {"type": "delete", "from_pos": 12, "to_pos": 18}
        ]
        has_conflict, message = check_operation_conflict(current_op, history_ops)
        assert has_conflict == True
        assert "已被删除" in message
    
    def test_delete_vs_replace_conflict(self):
        """测试删除与替换冲突"""
        current_op = {"type": "delete", "from_pos": 10, "to_pos": 15}
        history_ops = [
            {"type": "replace", "from_pos": 12, "to_pos": 18, "content": "new"}
        ]
        has_conflict, message = check_operation_conflict(current_op, history_ops)
        assert has_conflict == True
        assert "已被替换" in message
    
    def test_replace_vs_replace_conflict(self):
        """测试替换与替换冲突"""
        current_op = {"type": "replace", "from_pos": 10, "to_pos": 15, "content": "new1"}
        history_ops = [
            {"type": "replace", "from_pos": 12, "to_pos": 18, "content": "new2"}
        ]
        has_conflict, message = check_operation_conflict(current_op, history_ops)
        assert has_conflict == True
        assert "已被替换" in message
    
    def test_no_conflict_non_overlapping(self):
        """测试不重叠的操作不冲突"""
        current_op = {"type": "delete", "from_pos": 10, "to_pos": 15}
        history_ops = [
            {"type": "delete", "from_pos": 20, "to_pos": 25}
        ]
        has_conflict, message = check_operation_conflict(current_op, history_ops)
        assert has_conflict == False
    
    def test_format_no_conflict(self):
        """测试格式化操作不冲突"""
        current_op = {"type": "format", "from_pos": 10, "to_pos": 15, "marks": {}}
        history_ops = [
            {"type": "delete", "from_pos": 12, "to_pos": 18}
        ]
        has_conflict, message = check_operation_conflict(current_op, history_ops)
        assert has_conflict == False


class TestTransformOperationForConflictResolution:
    """测试操作变换"""
    
    def test_transform_insert(self):
        """测试插入操作的变换"""
        operation = {"type": "insert", "from_pos": 10, "to_pos": 10, "content": "abc"}
        history_ops = [
            {"type": "insert", "from_pos": 5, "to_pos": 5, "content": "xyz"}
        ]
        result = transform_operation_for_conflict_resolution(
            operation, history_ops, 20
        )
        assert result["from_pos"] == 13  # 10 + 3
        assert result["to_pos"] == 13
    
    def test_transform_delete(self):
        """测试删除操作的变换"""
        operation = {"type": "delete", "from_pos": 15, "to_pos": 20}
        history_ops = [
            {"type": "insert", "from_pos": 5, "to_pos": 5, "content": "abc"}
        ]
        result = transform_operation_for_conflict_resolution(
            operation, history_ops, 25
        )
        assert result["from_pos"] == 18  # 15 + 3
        assert result["to_pos"] == 23  # 20 + 3
    
    def test_transform_replace(self):
        """测试替换操作的变换"""
        operation = {"type": "replace", "from_pos": 15, "to_pos": 20, "content": "new"}
        history_ops = [
            {"type": "insert", "from_pos": 5, "to_pos": 5, "content": "abc"}
        ]
        result = transform_operation_for_conflict_resolution(
            operation, history_ops, 25
        )
        assert result["from_pos"] == 18  # 15 + 3
        assert result["to_pos"] == 23  # 20 + 3
    
    def test_transform_insert_out_of_bounds(self):
        """测试插入操作超出范围的处理"""
        operation = {"type": "insert", "from_pos": 10, "to_pos": 10, "content": "abc"}
        history_ops = []
        result = transform_operation_for_conflict_resolution(
            operation, history_ops, 5  # 内容长度只有5
        )
        assert result["from_pos"] == 5  # 调整到文档结尾
        assert result["to_pos"] == 5

