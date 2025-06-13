from typing import Dict, Any, List, Optional
import json
import uuid
from datetime import datetime

from langchain.llms.base import LLM
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langgraph import StateGraph, END
from langgraph.graph import Graph
from pydantic import BaseModel

from .tools import LocalCalculatorTool, LocalTextParserTool
from .config import settings
from ..models.schemas import TaskState, TaskStatus, UserRequest, TaskResponse


class OrchestratorState(BaseModel):
    """协调器状态模型"""
    task_id: str
    user_request: UserRequest
    current_step: str = "start"
    steps_completed: List[str] = []
    intermediate_results: Dict[str, Any] = {}
    final_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    messages: List[BaseMessage] = []
    
    class Config:
        arbitrary_types_allowed = True


class NexusMindOrchestrator:
    """NexusMind核心协调器"""
    
    def __init__(self):
        self.llm = self._initialize_llm()
        self.tools = self._initialize_tools()
        self.graph = self._build_graph()
        
    def _initialize_llm(self) -> LLM:
        """初始化LLM"""
        if settings.llm_provider == "openai":
            return ChatOpenAI(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url
            )
        else:
            # 可以扩展支持其他LLM提供商
            raise ValueError(f"不支持的LLM提供商: {settings.llm_provider}")
    
    def _initialize_tools(self) -> List:
        """初始化本地工具"""
        return [
            LocalCalculatorTool(),
            LocalTextParserTool()
        ]
    
    def _build_graph(self) -> StateGraph:
        """构建LangGraph决策图"""
        # 创建状态图
        workflow = StateGraph(OrchestratorState)
        
        # 添加节点
        workflow.add_node("analyze_request", self._analyze_request)
        workflow.add_node("plan_execution", self._plan_execution)
        workflow.add_node("execute_local_tools", self._execute_local_tools)
        workflow.add_node("format_response", self._format_response)
        
        # 设置入口点
        workflow.set_entry_point("analyze_request")
        
        # 添加边（决策路径）
        workflow.add_edge("analyze_request", "plan_execution")
        workflow.add_conditional_edges(
            "plan_execution",
            self._decide_execution_path,
            {
                "local_tools": "execute_local_tools",
                "format_response": "format_response"
            }
        )
        workflow.add_edge("execute_local_tools", "format_response")
        workflow.add_edge("format_response", END)
        
        return workflow.compile()
    
    async def process_request(self, user_request: UserRequest) -> TaskResponse:
        """处理用户请求"""
        task_id = str(uuid.uuid4())
        
        # 初始化状态
        initial_state = OrchestratorState(
            task_id=task_id,
            user_request=user_request,
            messages=[HumanMessage(content=user_request.message)]
        )
        
        try:
            # 执行图
            final_state = await self.graph.ainvoke(initial_state)
            
            # 返回响应
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                message="任务已完成",
                payload=final_state.final_result
            )
            
        except Exception as e:
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                message=f"处理失败: {str(e)}"
            )
    
    def _analyze_request(self, state: OrchestratorState) -> OrchestratorState:
        """分析用户请求"""
        state.current_step = "analyze_request"
        state.steps_completed.append("analyze_request")
        
        # 使用LLM分析用户意图
        analysis_prompt = f"""
        请分析以下用户请求：
        "{state.user_request.message}"
        
        请识别：
        1. 用户的主要意图
        2. 是否需要使用工具
        3. 需要哪些信息或计算
        
        以JSON格式返回分析结果。
        """
        
        try:
            response = self.llm.invoke(analysis_prompt)
            analysis = {
                "intent": "分析用户意图",
                "requires_tools": True,
                "analysis": response.content if hasattr(response, 'content') else str(response)
            }
            state.intermediate_results["request_analysis"] = analysis
        except Exception as e:
            state.intermediate_results["request_analysis"] = {
                "error": f"分析失败: {str(e)}"
            }
        
        return state
    
    def _plan_execution(self, state: OrchestratorState) -> OrchestratorState:
        """规划执行计划"""
        state.current_step = "plan_execution"
        state.steps_completed.append("plan_execution")
        
        user_message = state.user_request.message.lower()
        
        # 简单的规则匹配决定是否需要工具
        needs_calculation = any(op in user_message for op in ['+', '-', '*', '/', '计算', '算', 'calculate'])
        needs_text_parsing = any(keyword in user_message for keyword in ['解析', '分析', '提取', 'parse', 'analyze'])
        
        execution_plan = {
            "needs_local_tools": needs_calculation or needs_text_parsing,
            "tools_required": []
        }
        
        if needs_calculation:
            execution_plan["tools_required"].append("local_calculator")
        
        if needs_text_parsing:
            execution_plan["tools_required"].append("local_text_parser")
        
        state.intermediate_results["execution_plan"] = execution_plan
        return state
    
    def _decide_execution_path(self, state: OrchestratorState) -> str:
        """决定执行路径"""
        plan = state.intermediate_results.get("execution_plan", {})
        
        if plan.get("needs_local_tools", False):
            return "local_tools"
        else:
            return "format_response"
    
    def _execute_local_tools(self, state: OrchestratorState) -> OrchestratorState:
        """执行本地工具"""
        state.current_step = "execute_local_tools"
        state.steps_completed.append("execute_local_tools")
        
        plan = state.intermediate_results.get("execution_plan", {})
        tools_required = plan.get("tools_required", [])
        tool_results = {}
        
        user_message = state.user_request.message
        
        for tool_name in tools_required:
            try:
                if tool_name == "local_calculator":
                    # 提取数学表达式
                    calculator = LocalCalculatorTool()
                    # 简单提取：查找数学表达式模式
                    import re
                    math_patterns = re.findall(r'[\d+\-*/().]+', user_message)
                    if math_patterns:
                        expression = math_patterns[0]
                        result = calculator._run(expression)
                        tool_results["calculator"] = result
                    else:
                        tool_results["calculator"] = "未找到有效的数学表达式"
                
                elif tool_name == "local_text_parser":
                    parser = LocalTextParserTool()
                    result = parser._run(user_message, "general")
                    tool_results["text_parser"] = result
                    
            except Exception as e:
                tool_results[tool_name] = f"工具执行错误: {str(e)}"
        
        state.intermediate_results["tool_results"] = tool_results
        return state
    
    def _format_response(self, state: OrchestratorState) -> OrchestratorState:
        """格式化最终响应"""
        state.current_step = "format_response"
        state.steps_completed.append("format_response")
        
        # 收集所有结果
        analysis = state.intermediate_results.get("request_analysis", {})
        plan = state.intermediate_results.get("execution_plan", {})
        tool_results = state.intermediate_results.get("tool_results", {})
        
        # 构建最终响应
        response_data = {
            "user_request": state.user_request.message,
            "analysis": analysis,
            "execution_plan": plan,
            "results": tool_results,
            "timestamp": datetime.now().isoformat()
        }
        
        # 生成友好的回复消息
        if tool_results:
            reply_parts = ["根据您的请求，我已经处理完成："]
            for tool, result in tool_results.items():
                reply_parts.append(f"\n• {tool}: {result}")
            reply_message = "\n".join(reply_parts)
        else:
            reply_message = f"我已经收到您的消息：'{state.user_request.message}'。目前这是一个基础响应，更多功能正在开发中。"
        
        response_data["reply_message"] = reply_message
        state.final_result = response_data
        
        return state