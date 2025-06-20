#!/usr/bin/env python3
"""
NexusMind Simple Chat - 像ChatGPT一样简单，但支持语音和视觉
"""

import asyncio
import sys
import os
import json
import base64
import io
from datetime import datetime
from typing import Optional, List, Dict
import aiohttp
from rich.console import Console
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
from rich.status import Status

# 音视频库
try:
    import pyaudio
    import wave
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

try:
    import cv2
    from PIL import Image
    VIDEO_AVAILABLE = True
except ImportError:
    VIDEO_AVAILABLE = False

console = Console()

class SimpleChat:
    def __init__(self, api_url: str = "http://localhost:8080"):
        self.api_url = api_url
        self.conversation_history = []
        
    def record_audio(self) -> Optional[bytes]:
        """简单录音"""
        if not AUDIO_AVAILABLE:
            console.print("[red]未安装pyaudio，无法录音[/red]")
            return None
            
        try:
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            
            console.print("[yellow]🎤 录音中... 说完后按Enter停止[/yellow]")
            frames = []
            
            # 后台录音线程
            import threading
            stop_event = threading.Event()
            
            def record():
                while not stop_event.is_set():
                    try:
                        data = stream.read(1024, exception_on_overflow=False)
                        frames.append(data)
                    except:
                        break
                        
            record_thread = threading.Thread(target=record)
            record_thread.start()
            
            # 等待Enter
            input()
            stop_event.set()
            record_thread.join()
            
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            # 转WAV
            if frames:
                wav_buffer = io.BytesIO()
                wf = wave.open(wav_buffer, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b''.join(frames))
                wf.close()
                wav_buffer.seek(0)
                audio_data = wav_buffer.read()
                console.print(f"[green]✓ 录音完成，生成WAV文件大小: {len(audio_data)} bytes[/green]")
                return audio_data
            else:
                console.print("[red]没有收集到音频数据[/red]")
                return None
                
        except Exception as e:
            console.print(f"[red]录音失败: {e}[/red]")
            
        return None
        
    def capture_image(self) -> Optional[str]:
        """简单拍照"""
        if not VIDEO_AVAILABLE:
            console.print("[red]未安装opencv，无法拍照[/red]")
            return None
            
        try:
            cap = cv2.VideoCapture(0)
            console.print("[yellow]📷 拍照中... (3秒后自动捕获)[/yellow]")
            
            # 等待摄像头初始化并捕获
            import time
            time.sleep(1)  # 给摄像头初始化时间
            
            # 读取几帧来稳定摄像头
            for _ in range(5):
                ret, frame = cap.read()
                if ret:
                    break
                time.sleep(0.1)
                    
            if not ret:
                cap.release()
                console.print("[red]无法打开摄像头[/red]")
                return None
                
            # 最终捕获
            time.sleep(0.5)  # 额外等待确保图像质量
            ret, frame = cap.read()
            cap.release()  # 立即释放摄像头
            
            if ret:
                # 转base64
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_frame)
                buffer = io.BytesIO()
                pil_image.save(buffer, format='JPEG', quality=85)
                image_base64 = base64.b64encode(buffer.getvalue()).decode()
                
                console.print("[green]✓ 拍照成功[/green]")
                return image_base64
            
        except Exception as e:
            console.print(f"[red]拍照失败: {e}[/red]")
            
        return None
    
    def _is_photo_request(self, reply: str) -> bool:
        """检查回复是否包含自动拍照请求"""
        try:
            if reply.startswith('{') and '"action"' in reply and '"request_photo_capture"' in reply:
                return True
        except:
            pass
        return False
    
    async def _handle_auto_photo_request(self, reply: str, original_message: str) -> str:
        """处理自动拍照请求"""
        try:
            import json
            photo_request = json.loads(reply)
            purpose = photo_request.get("purpose", "回答您的问题")
            
            console.print(f"[yellow]📷 {photo_request.get('message', '正在自动拍照...')}[/yellow]")
            
            # 自动拍照
            image_data = self.capture_image()
            if image_data:
                console.print("[cyan]🔍 图像分析中...[/cyan]")
                # 用原始问题+图像数据重新请求
                return await self.send_message(original_message, image_data=image_data)
            else:
                return f"自动拍照失败，无法{purpose}。请手动拍照或检查摄像头设置。"
                
        except Exception as e:
            console.print(f"[red]处理自动拍照请求时出错: {e}[/red]")
            return "自动拍照功能出现问题，请手动拍照。"
        
    async def send_message(self, message: str, audio_data: bytes = None, image_data: str = None) -> str:
        """发送消息到后端"""
        try:
            payload = {
                "message": message,
                "metadata": {
                    "conversation_history": self.conversation_history[-10:]  # 最近10条
                }
            }
            
            # 添加音频数据
            if audio_data:
                encoded_audio = base64.b64encode(audio_data).decode()
                payload["audio_data"] = encoded_audio
                payload["metadata"]["action"] = "speech_to_text"
                payload["metadata"]["audio_format"] = "wav"
                console.print(f"[dim]音频base64编码长度: {len(encoded_audio)}[/dim]")
                
            # 添加图像数据
            if image_data:
                payload["image_data"] = image_data
                
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/api/v1/chat", json=payload) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        # API返回格式: {"payload": {"reply_message": "..."}}
                        payload = result.get("payload", {})
                        reply = payload.get("reply_message", payload.get("reply", "无回复"))
                        
                        # 检查是否是自动拍照请求
                        if self._is_photo_request(reply):
                            return await self._handle_auto_photo_request(reply, message)
                        
                        return reply
                    else:
                        error_text = await resp.text()
                        return f"服务器错误 {resp.status}: {error_text}"
                        
        except Exception as e:
            return f"连接错误: {str(e)}"
            
    async def run(self):
        """主循环"""
        console.clear()
        
        # 简单的欢迎界面
        console.print(Panel.fit(
            "[bold cyan]NexusMind Chat[/bold cyan]\n"
            "[dim]支持文字、语音、图像的智能助手[/dim]",
            border_style="cyan"
        ))
        
        console.print("\n命令：")
        console.print("  • 直接输入文字对话")
        console.print("  • 输入 'voice' 或 'v' 使用语音")
        console.print("  • 输入 'photo' 或 'p' 拍照")
        console.print("  • 输入 'quit' 或 'q' 退出")
        console.print("  • 输入 'clear' 清屏\n")
        
        while True:
            try:
                # 简单的输入提示
                user_input = Prompt.ask("\n[bold green]You[/bold green]")
                
                # 处理命令
                if user_input.lower() in ['quit', 'q']:
                    console.print("[yellow]再见！[/yellow]")
                    break
                    
                elif user_input.lower() == 'clear':
                    console.clear()
                    continue
                    
                elif user_input.lower() in ['voice', 'v']:
                    # 语音输入
                    audio_data = self.record_audio()
                    if audio_data:
                        console.print(f"[dim]音频数据大小: {len(audio_data)} bytes[/dim]")
                        with console.status("[cyan]🎤 识别中...[/cyan]") as status:
                            # 直接请求语音识别，不是请求“语音转文字”文本
                            response = await self.send_message("请识别我的语音内容", audio_data=audio_data)
                        
                        # 显示识别结果
                        console.print(f"[yellow]识别内容: {response}[/yellow]")
                        
                        # 检查是否成功识别
                        if response and not response.startswith("错误") and not response.startswith("未识别到"):
                            # 提取识别内容
                            extracted_text = ""
                            if "识别结果：" in response:
                                extracted_text = response.split("识别结果：", 1)[1].strip()
                            elif "识别到：" in response:
                                extracted_text = response.split("识别到：", 1)[1].strip()
                            else:
                                # 如果没有特定格式，去除前缀
                                extracted_text = response.replace("语音识别结果：", "").replace("语音转文字：", "").strip()
                            
                            # 如果成功提取到文本，继续处理
                            if extracted_text and len(extracted_text) > 3:  # 至少有几个字符
                                user_input = extracted_text
                                console.print(f"[green]✓ 识别成功: {user_input}[/green]")
                                
                                # 以识别结果作为新的用户输入，继续对话
                                with console.status("[cyan]🤖 思考中...[/cyan]") as status:
                                    response = await self.send_message(user_input)
                            else:
                                console.print("[yellow]识别到的内容太短或为空，请重新录音[/yellow]")
                                continue
                        else:
                            console.print("[yellow]未能识别语音内容，请重新录音[/yellow]")
                            continue
                    else:
                        console.print("[red]未收集到音频数据[/red]")
                        continue
                        
                elif user_input.lower() in ['photo', 'p']:
                    # 拍照
                    image_data = self.capture_image()
                    if image_data:
                        # 询问要做什么
                        prompt = Prompt.ask("想让我分析什么", default="描述这张图片")
                        with console.status("[cyan]🖼️ 分析中...[/cyan]") as status:
                            response = await self.send_message(prompt, image_data=image_data)
                    else:
                        continue
                        
                else:
                    # 普通文字对话
                    with console.status("[cyan]🤖 思考中...[/cyan]") as status:
                        response = await self.send_message(user_input)
                    
                # 保存到历史
                self.conversation_history.append({
                    "role": "user",
                    "content": user_input,
                    "timestamp": datetime.now().isoformat()
                })
                
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 显示回复
                console.print(f"\n[bold blue]NexusMind[/bold blue]: {response}")
                
            except KeyboardInterrupt:
                console.print("\n[yellow]使用 'quit' 退出[/yellow]")
                continue
            except Exception as e:
                console.print(f"[red]错误: {e}[/red]")


async def main():
    """主函数"""
    # 检查权限提示
    if sys.platform == "darwin":
        console.print("\n[yellow]macOS用户请确保终端有麦克风和摄像头权限[/yellow]")
        console.print("系统偏好设置 → 隐私与安全 → 麦克风/摄像头\n")
        
    # 检查后端
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8080/health") as resp:
                if resp.status != 200:
                    console.print("[red]后端服务未运行，请先启动: make start[/red]")
                    return
    except:
        console.print("[red]无法连接到后端服务[/red]")
        console.print("[yellow]请先启动后端: make start[/yellow]")
        return
        
    chat = SimpleChat()
    await chat.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]再见！[/yellow]")