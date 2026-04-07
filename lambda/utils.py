"""
Utility Functions Module

Contains helper functions for sorting, filtering, and validation.
"""

from typing import List


def sort_chunks_by_confidence(chunks: List[dict]) -> List[dict]:
    """
    按置信度降序排列召回内容
    
    对于任意问答响应中的召回内容列表，列表中的元素应按 confidenceScore 降序排列，
    即对于任意相邻元素 chunks[i] 和 chunks[i+1]，
    chunks[i].confidenceScore >= chunks[i+1].confidenceScore。
    
    Args:
        chunks: 召回内容列表，每个元素应包含 'confidenceScore' 字段
        
    Returns:
        按 confidenceScore 降序排列的新列表
        
    验证: 需求 3.4 - THE QA_System SHALL 按 Confidence_Score 降序排列召回内容
    """
    return sorted(chunks, key=lambda x: x.get('confidenceScore', 0.0), reverse=True)


def filter_chunks_by_confidence(chunks: List[dict], threshold: float) -> List[dict]:
    """
    按置信度阈值过滤召回内容
    
    对于任意置信度阈值 T 和召回内容列表，过滤后显示的所有内容项的 
    confidenceScore 都应大于或等于 T。
    
    Args:
        chunks: 召回内容列表，每个元素应包含 'confidenceScore' 字段
        threshold: 置信度阈值，范围应为 [0.0, 1.0]
        
    Returns:
        仅包含 confidenceScore >= threshold 的元素的新列表
        
    验证: 需求 6.3 - WHEN 显示召回内容 THEN QA_System SHALL 仅显示 
          Confidence_Score 高于阈值的 Retrieved_Chunk
    """
    return [chunk for chunk in chunks if chunk.get('confidenceScore', 0.0) >= threshold]


def clamp_confidence_threshold(value: float) -> float:
    """
    将置信度阈值限制在有效范围内 [0.0, 1.0]
    
    对于任意置信度阈值设置操作，设置的值应在 [0.0, 1.0] 范围内。
    超出范围的值应被限制到边界值。
    
    Args:
        value: 输入值，可以是任意浮点数
        
    Returns:
        限制在 [0.0, 1.0] 范围内的值
        - 如果 value < 0.0，返回 0.0
        - 如果 value > 1.0，返回 1.0
        - 否则返回原值
        
    验证: 需求 6.1 - THE QA_System SHALL 提供置信度阈值滑块，范围为 0.0 到 1.0
    """
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def generate_session_id() -> str:
    """
    生成唯一的会话 ID
    
    Returns:
        UUID 字符串
    """
    import uuid
    return str(uuid.uuid4())
