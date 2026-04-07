"""
Strands Agent Module

Encapsulates the Strands Agent for RAG-based question answering
using Amazon Bedrock Knowledge Base.

Requirements:
- 2.2: WHEN 后端收到问题 THEN Lambda_Handler SHALL 调用 Strands_Agent 进行知识检索和回答生成
- 2.3: WHEN Strands_Agent 处理完成 THEN QA_System SHALL 返回包含答案和召回内容的完整响应
"""

import os
import uuid
import logging
from typing import List, Tuple, Optional, Any

from strands import Agent
from strands.models import BedrockModel
from strands_tools import retrieve

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class QAAgentError(Exception):
    """QA Agent 相关错误的基类"""
    pass


class KnowledgeBaseError(QAAgentError):
    """知识库调用错误"""
    pass


class ModelInvocationError(QAAgentError):
    """模型调用错误"""
    pass


class QAAgent:
    """
    问答 Agent 封装类
    
    封装 Strands Agent 和 retrieve 工具，用于基于 Bedrock Knowledge Base 的 RAG 问答。
    
    Attributes:
        knowledge_base_id: Bedrock Knowledge Base ID
        model_id: Bedrock 模型 ID
        system_prompt: 系统提示词
        region: AWS 区域
        max_tokens: 最大输出 token 数
        temperature: 温度参数
    """
    
    def __init__(
        self,
        knowledge_base_id: str,
        model_id: str,
        system_prompt: str,
        region: str = "us-west-2",
        max_tokens: int = 4096,
        temperature: float = 0.3
    ):
        """
        初始化 Agent
        
        Args:
            knowledge_base_id: Bedrock Knowledge Base ID
            model_id: Bedrock 模型 ID
            system_prompt: 系统提示词
            region: AWS 区域
            max_tokens: 最大输出 token 数
            temperature: 温度参数
            
        Raises:
            ValueError: 当 knowledge_base_id 为空时
        """
        if not knowledge_base_id:
            raise ValueError("knowledge_base_id is required")
        
        self.knowledge_base_id = knowledge_base_id
        self.model_id = model_id
        self.system_prompt = system_prompt
        self.region = region
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Set environment variable for retrieve tool (required by strands_tools)
        os.environ["KNOWLEDGE_BASE_ID"] = knowledge_base_id
        
        # Initialize Bedrock model
        self._model = BedrockModel(
            model_id=model_id,
            region=region,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Initialize Strands Agent with retrieve tool for RAG
        self._agent = Agent(
            model=self._model,
            system_prompt=system_prompt,
            tools=[retrieve]
        )
        
        # Store retrieved chunks from the last query
        self._last_retrieved_chunks: List[dict] = []
        
        logger.info(
            f"QAAgent initialized with model={model_id}, "
            f"knowledge_base={knowledge_base_id}, region={region}"
        )
    
    def ask(
        self,
        question: str,
        confidence_threshold: float = 0.5
    ) -> Tuple[str, List[dict]]:
        """
        执行问答

        使用 Strands Agent 调用 Bedrock Knowledge Base 进行知识检索，
        然后使用大模型生成回答。

        Args:
            question: 用户问题
            confidence_threshold: 置信度阈值，用于过滤召回内容

        Returns:
            (答案, 召回内容列表) 元组
            召回内容列表中每个元素包含:
            - chunk_id: 片段唯一标识
            - content: 原文内容
            - confidence_score: 置信度分数
            - source: 来源信息

        Raises:
            ValueError: 当问题为空时
            KnowledgeBaseError: 当知识库调用失败时
            ModelInvocationError: 当模型调用失败时
        """
        if not question or not question.strip():
            raise ValueError("question cannot be empty")

        # Clamp confidence threshold to valid range
        confidence_threshold = max(0.0, min(1.0, confidence_threshold))

        logger.info(f"Processing question: {question[:100]}... with confidence threshold: {confidence_threshold}")

        try:
            # CRITICAL FIX: Clear agent messages history to prevent state pollution across requests
            # Without this, messages from previous questions accumulate and cause incorrect chunk extraction
            print(f"[DEBUG] Before reset - agent.messages count: {len(self._agent.messages) if self._agent.messages else 0}")
            self._agent.messages = []  # Reset conversation history
            print(f"[DEBUG] After reset - agent.messages count: {len(self._agent.messages)}")

            # Temporarily update the system prompt to include confidence threshold
            original_system = self._agent.system_prompt
            enhanced_system = (
                f"{original_system}\n\n"
                f"CRITICAL INSTRUCTION: When you use the retrieve tool to search the knowledge base, "
                f"you MUST set the 'score' parameter to {confidence_threshold}. This ensures that only "
                f"knowledge base results with relevance score >= {confidence_threshold} are retrieved "
                f"and used to answer the user's question. Do not use results with lower scores."
            )
            self._agent.system_prompt = enhanced_system

            # Invoke Strands Agent
            response = self._agent(question)

            # Restore original system prompt
            self._agent.system_prompt = original_system
            
            # Log response structure for debugging (using print for Lambda visibility)
            print(f"[DEBUG] Response type: {type(response).__name__}")
            print(f"[DEBUG] Response dir: {[a for a in dir(response) if not a.startswith('_')]}")
            logger.info(f"Response type: {type(response).__name__}")
            logger.info(f"Response dir: {[a for a in dir(response) if not a.startswith('_')]}")
            
            # 关键：通过 agent.messages 访问消息历史，而不是 response.state
            print(f"[DEBUG] Accessing agent.messages...")
            agent_messages = self._agent.messages
            print(f"[DEBUG] agent.messages type: {type(agent_messages).__name__}")
            print(f"[DEBUG] agent.messages count: {len(agent_messages) if agent_messages else 0}")
            
            # Extract answer from response
            answer = self._extract_answer(response)
            
            # Extract retrieved chunks from agent.messages
            retrieved_chunks = self._extract_chunks_from_messages(agent_messages, confidence_threshold)
            
            logger.info(
                f"Question processed successfully. "
                f"Answer length: {len(answer)}, Retrieved chunks: {len(retrieved_chunks)}"
            )
            
            return answer, retrieved_chunks
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error processing question: {error_msg}")
            
            # Categorize the error
            if "knowledge" in error_msg.lower() or "retrieve" in error_msg.lower():
                raise KnowledgeBaseError(f"Knowledge base error: {error_msg}") from e
            elif "model" in error_msg.lower() or "invoke" in error_msg.lower():
                raise ModelInvocationError(f"Model invocation error: {error_msg}") from e
            else:
                raise QAAgentError(f"Agent error: {error_msg}") from e
    
    def _extract_chunks_from_messages(
        self,
        messages: List[Any],
        confidence_threshold: float
    ) -> List[dict]:
        """
        从 agent.messages 中提取召回的知识库片段

        strands_tools retrieve 返回的格式是文本字符串:
        "Retrieved N results with score >= X:
        Score: 0.6419
        Document ID: s3://...
        Content: ...
        Metadata: {...}

        Score: 0.5536
        ..."

        Args:
            messages: agent.messages 列表
            confidence_threshold: 置信度阈值

        Returns:
            召回内容列表，按置信度降序排列
        """
        chunks = []

        if not messages:
            print("[DEBUG] No messages to extract chunks from")
            return chunks

        print(f"[DEBUG] Extracting chunks from {len(messages)} messages")

        try:
            for i, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    continue

                # Log message structure for debugging
                msg_role = msg.get('role', 'unknown')
                print(f"[DEBUG] Message {i}: role={msg_role}")

                content = msg.get('content', [])
                if not isinstance(content, list):
                    continue

                for j, item in enumerate(content):
                    if not isinstance(item, dict):
                        continue

                    # 查找 toolResult
                    if 'toolResult' in item:
                        tool_result = item['toolResult']
                        status = tool_result.get('status', '')
                        tool_use_id = tool_result.get('toolUseId', 'unknown')

                        print(f"[DEBUG] Found toolResult in message {i}, content {j}: status={status}, toolUseId={tool_use_id}")

                        # 只处理成功的结果
                        if status != 'success':
                            print(f"[DEBUG] Skipping toolResult with status: {status}")
                            continue

                        if isinstance(tool_result, dict):
                            tr_content = tool_result.get('content', [])

                            if isinstance(tr_content, list):
                                for k, tr_item in enumerate(tr_content):
                                    if isinstance(tr_item, dict) and 'text' in tr_item:
                                        text = tr_item['text']
                                        print(f"[DEBUG] Parsing retrieve text result (toolUseId={tool_use_id}), length: {len(text)}")

                                        # 解析 strands_tools retrieve 的文本格式
                                        parsed_chunks = self._parse_retrieve_text_format(text)
                                        print(f"[DEBUG] Parsed {len(parsed_chunks)} chunks from text (toolUseId={tool_use_id})")
                                        chunks.extend(parsed_chunks)

            print(f"[DEBUG] Total chunks extracted from all messages: {len(chunks)}")

            # Deduplicate chunks by chunk_id (keep the one with highest score)
            seen_chunk_ids = {}
            for chunk in chunks:
                chunk_id = chunk.get("chunk_id")
                score = chunk.get("confidence_score", 0)

                if chunk_id not in seen_chunk_ids or seen_chunk_ids[chunk_id]["confidence_score"] < score:
                    seen_chunk_ids[chunk_id] = chunk

            deduplicated_chunks = list(seen_chunk_ids.values())
            print(f"[DEBUG] Chunks after deduplication: {len(deduplicated_chunks)} (removed {len(chunks) - len(deduplicated_chunks)} duplicates)")

            # Filter by confidence threshold
            filtered_chunks = [
                chunk for chunk in deduplicated_chunks
                if chunk.get("confidence_score", 0) >= confidence_threshold
            ]

            # Sort by confidence score descending
            filtered_chunks.sort(
                key=lambda x: x.get("confidence_score", 0),
                reverse=True
            )

            print(f"[DEBUG] Chunks after filtering (threshold={confidence_threshold}): {len(filtered_chunks)}")

            # WARN: If no chunks found after filtering
            if len(filtered_chunks) == 0 and len(chunks) > 0:
                print(f"[WARN] All {len(chunks)} retrieved chunks were filtered out by confidence threshold {confidence_threshold}")
                print(f"[WARN] Consider lowering the threshold or improving knowledge base content")
            elif len(filtered_chunks) == 0:
                print(f"[WARN] No chunks retrieved from knowledge base - retrieve tool may have returned empty results")

            return filtered_chunks
            
        except Exception as e:
            print(f"[DEBUG] Error extracting chunks from messages: {e}")
            import traceback
            print(f"[DEBUG] {traceback.format_exc()}")
            return []
    
    def _parse_retrieve_text_format(self, text: str) -> List[dict]:
        """
        解析 strands_tools retrieve 返回的文本格式
        
        格式示例:
        "Retrieved 5 results with score >= 0.4:
        Score: 0.6419
        Document ID: s3://bucket/file.csv
        Content: 问题内容
        Metadata: {'key': 'value', ...}
        
        Score: 0.5536
        ..."
        
        Args:
            text: retrieve 工具返回的文本
            
        Returns:
            解析后的 chunk 列表
        """
        chunks = []
        
        if not text or not text.startswith("Retrieved"):
            return chunks
        
        import re
        import ast
        
        # 按 "Score:" 分割，获取每个结果块
        # 跳过第一部分（"Retrieved N results..."）
        parts = re.split(r'\nScore:\s*', text)
        
        for i, part in enumerate(parts[1:], 1):  # 跳过第一部分
            try:
                lines = part.strip().split('\n')
                if not lines:
                    continue
                
                # 第一行是分数
                score_str = lines[0].strip()
                try:
                    score = float(score_str)
                except ValueError:
                    score = 0.0
                
                # 解析其他字段
                doc_id = ""
                content = ""
                metadata = {}
                
                current_field = None
                current_value = []
                
                for line in lines[1:]:
                    if line.startswith("Document ID:"):
                        if current_field and current_value:
                            self._set_chunk_field(current_field, '\n'.join(current_value), 
                                                  locals())
                        current_field = "doc_id"
                        current_value = [line[len("Document ID:"):].strip()]
                    elif line.startswith("Content:"):
                        if current_field == "doc_id":
                            doc_id = '\n'.join(current_value)
                        current_field = "content"
                        current_value = [line[len("Content:"):].strip()]
                    elif line.startswith("Metadata:"):
                        if current_field == "content":
                            content = '\n'.join(current_value)
                        current_field = "metadata"
                        current_value = [line[len("Metadata:"):].strip()]
                    else:
                        # 继续当前字段
                        if current_field:
                            current_value.append(line)
                
                # 处理最后一个字段
                if current_field == "doc_id":
                    doc_id = '\n'.join(current_value)
                elif current_field == "content":
                    content = '\n'.join(current_value)
                elif current_field == "metadata":
                    metadata_str = '\n'.join(current_value)
                    try:
                        metadata = ast.literal_eval(metadata_str)
                    except:
                        metadata = {}
                
                # 从 metadata 中提取 Answer（如果有）
                answer = metadata.get('Answer', '')

                # 只保留有 Answer 的 chunks（真正的QA对）
                # 没有Answer的content只是问题文本,不需要显示
                if answer and metadata.get('x-amz-bedrock-kb-chunk-id'):
                    chunk = {
                        "chunk_id": metadata.get('x-amz-bedrock-kb-chunk-id'),
                        "content": answer,  # 显示答案
                        "confidence_score": score,
                        "source": doc_id,
                        "question": content,  # 问题文本
                        "metadata": metadata
                    }
                    chunks.append(chunk)
                    print(f"[DEBUG] Parsed valid QA chunk: chunk_id={chunk['chunk_id']}, score={score}")
                    print(f"[DEBUG]   Question: {content[:50]}...")
                    print(f"[DEBUG]   Answer: {answer[:50]}...")
                else:
                    if not answer:
                        print(f"[DEBUG] Skipping chunk without Answer (only has question, score={score})")
                    else:
                        print(f"[DEBUG] Skipping chunk without valid chunk_id (score={score})")
                    
            except Exception as e:
                print(f"[DEBUG] Error parsing chunk {i}: {e}")
                continue
        
        return chunks
    
    def _extract_answer(self, response: Any) -> str:
        """
        从 Agent 响应中提取答案文本
        
        Args:
            response: Strands Agent 响应对象
            
        Returns:
            答案文本
        """
        # Handle different response formats from Strands Agent
        result = None
        
        if hasattr(response, 'message'):
            result = response.message
        elif hasattr(response, 'content'):
            result = response.content
        elif hasattr(response, 'text'):
            result = response.text
        else:
            result = response
        
        # Handle dict format: {'role': 'assistant', 'content': [{'text': '...'}]}
        if isinstance(result, dict):
            if 'content' in result:
                content = result['content']
                if isinstance(content, list) and len(content) > 0:
                    first_item = content[0]
                    if isinstance(first_item, dict) and 'text' in first_item:
                        return first_item['text']
                    return str(first_item)
                elif isinstance(content, str):
                    return content
            if 'text' in result:
                return result['text']
            if 'message' in result:
                return str(result['message'])
        
        # Handle list format: [{'text': '...'}]
        if isinstance(result, list) and len(result) > 0:
            first_item = result[0]
            if isinstance(first_item, dict) and 'text' in first_item:
                return first_item['text']
            return str(first_item)
        
        return str(result)
    
    def _parse_tool_result_content(self, tool_result: dict) -> List[dict]:
        """
        解析 toolResult 内容
        
        Args:
            tool_result: toolResult 字典
            
        Returns:
            解析后的召回内容列表
        """
        chunks = []
        content = tool_result.get('content', [])
        print(f"[DEBUG] _parse_tool_result_content: content type={type(content)}, len={len(content) if isinstance(content, list) else 'N/A'}")
        
        for i, item in enumerate(content):
            if isinstance(item, dict):
                print(f"[DEBUG] content[{i}] keys: {list(item.keys())}")
                # Check for JSON content with retrieval results
                json_data = item.get('json') or item.get('text')
                if json_data:
                    print(f"[DEBUG] Found json/text data, type={type(json_data)}")
                    if isinstance(json_data, str):
                        try:
                            import json as json_module
                            json_data = json_module.loads(json_data)
                            print(f"[DEBUG] Parsed JSON string, type={type(json_data)}")
                        except Exception as e:
                            print(f"[DEBUG] Failed to parse JSON: {e}")
                            continue
                    
                    if isinstance(json_data, dict):
                        print(f"[DEBUG] json_data keys: {list(json_data.keys())}")
                        # Look for retrievalResults
                        retrieval_results = (
                            json_data.get('retrievalResults') or 
                            json_data.get('results') or
                            json_data.get('ResponseBody', {}).get('retrievalResults') or
                            []
                        )
                        
                        print(f"[DEBUG] Found {len(retrieval_results)} retrievalResults")
                        for result_item in retrieval_results:
                            chunk = self._parse_single_chunk(result_item)
                            if chunk:
                                chunks.append(chunk)
        
        print(f"[DEBUG] _parse_tool_result_content returning {len(chunks)} chunks")
        return chunks
    
    def _get_tool_results(self, response: Any) -> List[Any]:
        """
        从响应中获取工具调用结果
        
        Args:
            response: Agent 响应对象
            
        Returns:
            工具结果列表
        """
        results = []
        
        # Log response structure for debugging
        logger.info(f"Extracting tool results from response type: {type(response)}")
        
        # Try different ways to access tool results
        if hasattr(response, 'tool_results'):
            logger.info(f"Found tool_results: {type(response.tool_results)}")
            results = response.tool_results or []
        elif hasattr(response, 'tool_calls'):
            logger.info(f"Found tool_calls: {type(response.tool_calls)}")
            results = response.tool_calls or []
        elif hasattr(response, 'messages'):
            # Extract from message history
            logger.info(f"Found messages: {len(response.messages) if response.messages else 0}")
            for msg in (response.messages or []):
                if hasattr(msg, 'tool_results'):
                    results.extend(msg.tool_results or [])
        
        # Check for tool_use in the response
        if hasattr(response, 'tool_use'):
            logger.info(f"Found tool_use: {type(response.tool_use)}")
            if response.tool_use:
                results.append(response.tool_use)
        
        # Check for state with tool results
        if hasattr(response, 'state'):
            state = response.state
            if hasattr(state, 'tool_results'):
                logger.info(f"Found state.tool_results")
                results.extend(state.tool_results or [])
            if hasattr(state, 'messages'):
                for msg in (state.messages or []):
                    if isinstance(msg, dict) and 'toolResult' in msg:
                        results.append(msg['toolResult'])
                    elif hasattr(msg, 'content'):
                        content = msg.content
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and 'toolResult' in item:
                                    results.append(item['toolResult'])
        
        # Also check for retrieve results in the response metadata
        if hasattr(response, 'metadata') and response.metadata:
            if 'retrieve_results' in response.metadata:
                results.append(response.metadata['retrieve_results'])
        
        logger.info(f"Total tool results found: {len(results)}")
        return results
    
    def _is_retrieve_result(self, result: Any) -> bool:
        """
        检查结果是否来自 retrieve 工具
        
        Args:
            result: 工具结果
            
        Returns:
            是否为 retrieve 工具结果
        """
        if isinstance(result, dict):
            # Check for common retrieve result indicators
            return (
                'retrievalResults' in result or
                'results' in result or
                result.get('tool_name') == 'retrieve' or
                result.get('name') == 'retrieve'
            )
        
        if hasattr(result, 'tool_name'):
            return result.tool_name == 'retrieve'
        
        return False
    
    def _parse_retrieve_result(self, result: Any) -> List[dict]:
        """
        解析 retrieve 工具的结果
        
        Args:
            result: retrieve 工具结果
            
        Returns:
            解析后的召回内容列表
        """
        chunks = []
        
        # Handle dict result
        if isinstance(result, dict):
            # Try different result formats
            retrieval_results = (
                result.get('retrievalResults') or 
                result.get('results') or 
                result.get('output', {}).get('retrievalResults') or
                []
            )
            
            for item in retrieval_results:
                chunk = self._parse_single_chunk(item)
                if chunk:
                    chunks.append(chunk)
        
        # Handle object result
        elif hasattr(result, 'output'):
            output = result.output
            if isinstance(output, dict):
                retrieval_results = output.get('retrievalResults', [])
                for item in retrieval_results:
                    chunk = self._parse_single_chunk(item)
                    if chunk:
                        chunks.append(chunk)
        
        return chunks
    
    def _parse_single_chunk(self, item: Any) -> Optional[dict]:
        """
        解析单个召回片段
        
        Args:
            item: 召回片段数据
            
        Returns:
            格式化的召回内容字典，或 None
        """
        if not isinstance(item, dict):
            return None
        
        # Extract content
        content = ""
        if 'content' in item:
            content_data = item['content']
            if isinstance(content_data, dict):
                content = content_data.get('text', '')
            else:
                content = str(content_data)
        elif 'text' in item:
            content = item['text']
        
        if not content:
            return None
        
        # Extract confidence score
        confidence_score = item.get('score', 0.0)
        if isinstance(confidence_score, str):
            try:
                confidence_score = float(confidence_score)
            except ValueError:
                confidence_score = 0.0
        
        # Extract source information
        source = ""
        if 'location' in item:
            location = item['location']
            if isinstance(location, dict):
                # Try S3 location
                s3_location = location.get('s3Location', {})
                source = s3_location.get('uri', '')
                if not source:
                    # Try other location types
                    source = location.get('uri', '') or location.get('url', '')
            else:
                source = str(location)
        elif 'source' in item:
            source = str(item['source'])
        
        # Generate chunk ID
        chunk_id = item.get('id') or item.get('chunkId') or str(uuid.uuid4())
        
        return {
            "chunk_id": chunk_id,
            "content": content,
            "confidence_score": confidence_score,
            "source": source
        }


def create_agent_from_config(config: "Config") -> QAAgent:
    """
    从配置对象创建 QAAgent 实例
    
    Args:
        config: Config 配置对象
        
    Returns:
        QAAgent 实例
    """
    return QAAgent(
        knowledge_base_id=config.knowledge_base_id,
        model_id=config.model_id,
        system_prompt=config.system_prompt,
        region=config.aws_region,
        max_tokens=config.max_tokens,
        temperature=config.temperature
    )
