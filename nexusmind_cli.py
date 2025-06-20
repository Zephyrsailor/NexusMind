#!/usr/bin/env python3
"""
NexusMind CLI - Production Terminal Client
Real-time multi-agent system monitor and controller
"""

import asyncio
import json
import sys
import signal
from datetime import datetime
from typing import Dict, List, Optional
import aiohttp
import websockets
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

class NexusMindCLI:
    def __init__(self, api_url: str = "http://localhost:8080"):
        self.api_url = api_url
        self.ws_url = api_url.replace("http://", "ws://") + "/ws/monitor"
        self.agents_status = {}
        self.transcriptions = []
        self.shared_context = {}
        self.active_tasks = {}
        self.running = True
        self.ws = None
        self.recording = False
        self.current_task_id = None
        
    def create_layout(self) -> Layout:
        """Create the terminal layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=4)
        )
        
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=2)
        )
        
        layout["left"].split_column(
            Layout(name="agents"),
            Layout(name="tasks", size=10)
        )
        
        layout["right"].split_column(
            Layout(name="transcription"),
            Layout(name="context")
        )
        
        return layout
        
    def render_header(self) -> Panel:
        """Render header with status"""
        status = "🟢 Connected" if self.ws else "🔴 Disconnected"
        recording_status = "🔴 Recording" if self.recording else ""
        
        header_text = Text()
        header_text.append("🧠 NexusMind CLI ", style="bold magenta")
        header_text.append(f"| {status} ", style="green" if self.ws else "red")
        header_text.append(f"| {datetime.now().strftime('%H:%M:%S')} ", style="dim")
        if recording_status:
            header_text.append(f"| {recording_status}", style="red bold")
            
        return Panel(header_text, style="cyan")
        
    def render_agents(self) -> Panel:
        """Render agents status table"""
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Agent", width=20)
        table.add_column("Status", width=10)
        table.add_column("Task", width=15)
        
        for agent_id, status in self.agents_status.items():
            status_text = status.get("status", "unknown")
            color = "green" if status_text == "active" else "yellow" if status_text == "busy" else "dim"
            
            table.add_row(
                agent_id.replace("_", " ").title()[:20],
                f"[{color}]● {status_text}[/{color}]",
                str(status.get("current_task", "-"))[:15]
            )
            
        return Panel(table, title="🤖 Agent Status", border_style="green")
        
    def render_tasks(self) -> Panel:
        """Render active tasks"""
        content = Text()
        
        if not self.active_tasks:
            content.append("No active tasks", style="dim")
        else:
            for task_id, task_info in list(self.active_tasks.items())[:5]:
                content.append(f"• {task_id[:8]}... ", style="cyan")
                content.append(f"{task_info.get('status', 'unknown')}\n", style="yellow")
                
        return Panel(content, title="📋 Active Tasks", border_style="yellow")
        
    def render_transcription(self) -> Panel:
        """Render voice transcriptions"""
        content = Text()
        
        if not self.transcriptions:
            content.append("No transcriptions yet...\n", style="dim")
            content.append("Press 'v' to start voice recording", style="dim italic")
        else:
            for trans in self.transcriptions[-8:]:  # Show last 8
                content.append(f"[{trans.get('time', '')}] ", style="dim cyan")
                content.append(f"{trans.get('text', '')}\n", style="white")
                
        return Panel(content, title="🎤 Voice Transcriptions", border_style="blue")
        
    def render_context(self) -> Panel:
        """Render shared context"""
        content = Text()
        
        if not self.shared_context:
            content.append("No shared context available", style="dim")
        else:
            # Show latest context updates
            for agent_id, context in list(self.shared_context.items())[:3]:
                content.append(f"\n{agent_id}:\n", style="bold yellow")
                if isinstance(context, dict):
                    for key, value in list(context.items())[:3]:
                        content.append(f"  {key}: {str(value)[:50]}...\n", style="white")
                        
        return Panel(content, title="📊 Shared Context", border_style="yellow")
        
    def render_footer(self) -> Panel:
        """Render command help"""
        commands = Table.grid(padding=0)
        commands.add_column(style="bold cyan", width=10)
        commands.add_column(style="white")
        
        commands.add_row("[V]oice", "Start/stop recording")
        commands.add_row("[T]ask", "Create new task")
        commands.add_row("[R]efresh", "Refresh status")
        commands.add_row("[Q]uit", "Exit application")
        
        return Panel(commands, title="Commands", style="dim")
        
    async def connect_websocket(self):
        """Connect to WebSocket for real-time updates"""
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self.ws = ws
                    console.print("[green]Connected to NexusMind WebSocket[/green]")
                    
                    while self.running:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            data = json.loads(message)
                            await self.handle_ws_message(data)
                        except asyncio.TimeoutError:
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            break
                            
            except Exception as e:
                self.ws = None
                console.print(f"[red]WebSocket connection failed: {e}[/red]")
                await asyncio.sleep(5)  # Retry after 5 seconds
                
    async def handle_ws_message(self, data: Dict):
        """Handle incoming WebSocket messages"""
        msg_type = data.get("type")
        
        if msg_type == "agent_status_update":
            agent_data = data.get("data", {})
            agent_id = agent_data.get("agent_id")
            if agent_id:
                self.agents_status[agent_id] = agent_data
                
        elif msg_type == "transcription_update":
            trans_data = data.get("data", {})
            self.transcriptions.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "text": trans_data.get("text", ""),
                "confidence": trans_data.get("confidence", 0)
            })
            
        elif msg_type == "context_update":
            context_data = data.get("data", {})
            agent_id = context_data.get("agent_id")
            if agent_id:
                self.shared_context[agent_id] = context_data.get("context", {})
                
        elif msg_type == "task_update":
            task_data = data.get("data", {})
            task_id = task_data.get("task_id")
            if task_id:
                self.active_tasks[task_id] = task_data
                
    async def fetch_initial_status(self):
        """Fetch initial status from API"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get agents status
                async with session.get(f"{self.api_url}/api/v1/agents/status") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for agent in data.get("agents", []):
                            self.agents_status[agent["agent_id"]] = agent
                            
                # Get dashboard data
                async with session.get(f"{self.api_url}/api/v1/monitor/dashboard") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.active_tasks = data.get("tasks", {})
                        
        except Exception as e:
            console.print(f"[red]Failed to fetch initial data: {e}[/red]")
            
    async def toggle_voice_recording(self):
        """Toggle voice recording on/off"""
        try:
            async with aiohttp.ClientSession() as session:
                if not self.recording:
                    # Start recording
                    self.current_task_id = f"voice_{int(datetime.now().timestamp())}"
                    payload = {
                        "task_id": self.current_task_id,
                        "action": "start_recording"
                    }
                    
                    async with session.post(
                        f"{self.api_url}/api/v1/agents/voice/test",
                        json=payload
                    ) as resp:
                        if resp.status == 200:
                            self.recording = True
                            console.print("[green]🔴 Voice recording started[/green]")
                        else:
                            console.print(f"[red]Failed to start recording: {resp.status}[/red]")
                else:
                    # Stop recording
                    payload = {
                        "task_id": self.current_task_id,
                        "action": "stop_recording"
                    }
                    
                    async with session.post(
                        f"{self.api_url}/api/v1/agents/voice/test",
                        json=payload
                    ) as resp:
                        if resp.status == 200:
                            self.recording = False
                            console.print("[yellow]⏹ Voice recording stopped[/yellow]")
                        else:
                            console.print(f"[red]Failed to stop recording: {resp.status}[/red]")
                            
        except Exception as e:
            console.print(f"[red]Voice control error: {e}[/red]")
            
    async def create_task(self):
        """Create a new task"""
        task_type = Prompt.ask("Task type", choices=["transcribe", "analyze", "detect"])
        description = Prompt.ask("Task description")
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "type": task_type,
                    "description": description,
                    "timestamp": datetime.now().isoformat()
                }
                
                async with session.post(
                    f"{self.api_url}/api/v1/tasks/create",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        console.print(f"[green]Task created: {result.get('task_id')}[/green]")
                    else:
                        console.print(f"[red]Failed to create task: {resp.status}[/red]")
                        
        except Exception as e:
            console.print(f"[red]Task creation error: {e}[/red]")
            
    async def handle_input(self, key: str):
        """Handle keyboard input"""
        if key.lower() == 'v':
            await self.toggle_voice_recording()
        elif key.lower() == 't':
            await self.create_task()
        elif key.lower() == 'r':
            await self.fetch_initial_status()
            console.print("[green]Status refreshed[/green]")
        elif key.lower() == 'q':
            if Confirm.ask("Really quit?"):
                self.running = False
                
    async def run(self):
        """Main run loop"""
        # Fetch initial data
        await self.fetch_initial_status()
        
        # Start WebSocket connection
        ws_task = asyncio.create_task(self.connect_websocket())
        
        # Create layout
        layout = self.create_layout()
        
        # Input handler
        async def input_handler():
            while self.running:
                try:
                    # This is a simplified approach - in production, use aioconsole
                    await asyncio.sleep(0.1)
                except Exception:
                    pass
                    
        input_task = asyncio.create_task(input_handler())
        
        # Main display loop
        try:
            with Live(layout, refresh_per_second=2) as live:
                while self.running:
                    # Update all panels
                    layout["header"].update(self.render_header())
                    layout["agents"].update(self.render_agents())
                    layout["tasks"].update(self.render_tasks())
                    layout["transcription"].update(self.render_transcription())
                    layout["context"].update(self.render_context())
                    layout["footer"].update(self.render_footer())
                    
                    await asyncio.sleep(0.5)
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
        finally:
            self.running = False
            ws_task.cancel()
            input_task.cancel()


def handle_signal(signum, frame):
    """Handle interrupt signals"""
    sys.exit(0)


async def main():
    """Main entry point"""
    signal.signal(signal.SIGINT, handle_signal)
    
    console.print("[bold cyan]🧠 NexusMind CLI - Multi-Agent System Monitor[/bold cyan]")
    console.print("[dim]Connecting to NexusMind backend...[/dim]\n")
    
    cli = NexusMindCLI()
    
    try:
        await cli.run()
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")