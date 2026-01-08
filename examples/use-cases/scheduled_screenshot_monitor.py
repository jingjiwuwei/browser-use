"""
Scheduled Screenshot Monitoring System

This example demonstrates:
1. Waiting for user login (including captcha handling)
2. Identifying and screenshotting multiple chart sections/blocks on a page
3. Saving screenshots with metadata (block name, timestamp, file path)
4. Scheduling periodic screenshot tasks

Requirements:
- User must complete first login manually (including any captcha)
- System then periodically captures screenshots of specified page sections
- Each screenshot is saved with metadata for tracking

Usage:
    python scheduled_screenshot_monitor.py --url "https://example.com/dashboard" --interval 300

Setup:
    1. Install browser-use: uv add browser-use
    2. Set your LLM API key (e.g., OPENAI_API_KEY or BROWSER_USE_API_KEY)
    3. Run the script and complete the login when prompted
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

from browser_use import ActionResult, Agent, BrowserSession, ChatBrowserUse, Tools
from browser_use.browser.views import BrowserState


class ScreenshotMetadata(BaseModel):
	"""Metadata for a screenshot."""

	timestamp: str = Field(..., description='ISO format timestamp when screenshot was taken')
	block_name: str = Field(..., description='Name/identifier of the page block/section')
	screenshot_path: str = Field(..., description='Relative path to the screenshot file')
	url: str = Field(..., description='URL of the page where screenshot was taken')


class ScreenshotBlock(BaseModel):
	"""Information about a block to screenshot."""

	name: str = Field(..., description='Name of the block/section')
	selector: str = Field(..., description='CSS selector for the block')


class ScheduledScreenshotMonitor:
	"""
	Manages scheduled screenshot monitoring of a website.

	Workflow:
	1. Wait for user to complete login manually
	2. Identify chart blocks on the page
	3. Periodically capture screenshots of each block
	4. Save screenshots and metadata
	"""

	def __init__(
		self,
		target_url: str,
		screenshot_dir: str = 'screenshots',
		metadata_file: str = 'screenshot_metadata.json',
		interval_seconds: int = 300,
	):
		"""
		Initialize the screenshot monitor.

		Args:
			target_url: URL of the website to monitor
			screenshot_dir: Directory to save screenshots
			metadata_file: JSON file to store metadata
			interval_seconds: Time interval between screenshot cycles (default: 5 minutes)
		"""
		self.target_url = target_url
		self.screenshot_dir = Path(screenshot_dir)
		self.metadata_file = Path(metadata_file)
		self.interval_seconds = interval_seconds
		self.browser_session: BrowserSession | None = None
		self.metadata_list: list[ScreenshotMetadata] = []

		# Create screenshot directory if it doesn't exist
		self.screenshot_dir.mkdir(parents=True, exist_ok=True)

		# Load existing metadata if available
		self._load_metadata()

	def _load_metadata(self) -> None:
		"""Load existing metadata from file."""
		if self.metadata_file.exists():
			try:
				with open(self.metadata_file, 'r', encoding='utf-8') as f:
					data = json.load(f)
					self.metadata_list = [ScreenshotMetadata(**item) for item in data]
				print(f'✅ Loaded {len(self.metadata_list)} existing metadata records')
			except Exception as e:
				print(f'⚠️ Could not load metadata: {e}')
				self.metadata_list = []

	def _save_metadata(self) -> None:
		"""Save metadata to file."""
		try:
			with open(self.metadata_file, 'w', encoding='utf-8') as f:
				data = [item.model_dump() for item in self.metadata_list]
				json.dump(data, f, indent=2, ensure_ascii=False)
			print(f'✅ Saved metadata to {self.metadata_file}')
		except Exception as e:
			print(f'❌ Failed to save metadata: {e}')

	async def wait_for_login(self) -> bool:
		"""
		Wait for user to complete login manually.

		This function:
		1. Opens the browser to the target URL
		2. Waits for user to manually complete login (including captcha)
		3. Confirms when user is ready to proceed

		Returns:
			True if login was successful and user confirmed
		"""
		print('\n' + '=' * 60)
		print('🔐 USER LOGIN REQUIRED')
		print('=' * 60)
		print(f'Opening browser to: {self.target_url}')
		print('\nPlease complete the following steps:')
		print('  1. Log in to the website (enter username, password)')
		print('  2. Complete any captcha verification if required')
		print('  3. Wait until you are fully logged in')
		print('=' * 60)

		# Initialize browser session with headless=False so user can interact
		self.browser_session = BrowserSession(headless=False)

		# Navigate to target URL
		await self.browser_session.goto(self.target_url)

		# Wait for user confirmation
		print('\n⏳ Waiting for login completion...')
		print('   Browser window is open - please complete login manually.')

		# Give user time to login - wait for input
		await asyncio.sleep(5)  # Initial wait to let page load

		# Simple loop to wait for user to press Enter
		loop = asyncio.get_event_loop()
		await loop.run_in_executor(
			None,
			lambda: input(
				'\n✋ After you have successfully logged in, press ENTER to continue with automated screenshot monitoring...\n'
			),
		)

		print('✅ Login confirmed! Starting automated monitoring...\n')
		return True

	async def identify_chart_blocks(self) -> list[ScreenshotBlock]:
		"""
		Identify chart blocks/sections on the page using AI.

		Returns:
			List of ScreenshotBlock objects with names and selectors
		"""
		print('🔍 Identifying chart blocks on the page...')

		if not self.browser_session:
			raise RuntimeError('Browser session not initialized')

		# Create an agent to identify chart blocks
		tools = Tools()
		blocks_found: list[ScreenshotBlock] = []

		@tools.action('Report identified chart blocks', param_model=list[ScreenshotBlock])
		async def report_blocks(params: list[ScreenshotBlock]) -> ActionResult:
			nonlocal blocks_found
			blocks_found = params
			return ActionResult(is_done=True, extracted_content=f'Found {len(params)} chart blocks')

		# Use agent to find chart blocks
		agent = Agent(
			task="""Analyze the current page and identify all chart/graph sections or dashboard blocks.
			For each chart or dashboard block you find:
			1. Give it a descriptive name (e.g., "Sales Chart", "Revenue Graph", "Performance Dashboard")
			2. Find a CSS selector that uniquely identifies that block (prefer IDs or unique classes)
			
			Look for elements like:
			- Canvas elements (charts are often rendered on canvas)
			- SVG elements (vector charts)
			- Div containers with chart/graph/dashboard related classes or IDs
			- Any section that appears to be a data visualization
			
			Report all the blocks you find using the report_blocks action.""",
			llm=ChatBrowserUse(),
			browser=self.browser_session,
			tools=tools,
		)

		try:
			await agent.run()
		except Exception as e:
			print(f'⚠️ Agent encountered an error: {e}')

		if blocks_found:
			print(f'✅ Identified {len(blocks_found)} chart blocks:')
			for block in blocks_found:
				print(f'   - {block.name}: {block.selector}')
		else:
			print('⚠️ No chart blocks identified. Will try to screenshot common chart elements.')
			# Fallback: use common chart selectors
			blocks_found = [
				ScreenshotBlock(name='Chart-Canvas', selector='canvas'),
				ScreenshotBlock(name='Chart-SVG', selector='svg'),
				ScreenshotBlock(name='Dashboard-Main', selector='.dashboard, .chart-container, .graph-container'),
			]

		return blocks_found

	async def capture_block_screenshots(self, blocks: list[ScreenshotBlock]) -> None:
		"""
		Capture screenshots of specified blocks.

		Args:
			blocks: List of blocks to screenshot
		"""
		if not self.browser_session:
			raise RuntimeError('Browser session not initialized')

		timestamp = datetime.now().isoformat()
		timestamp_safe = datetime.now().strftime('%Y%m%d_%H%M%S')
		current_url = await self._get_current_url()

		print(f'\n📸 Capturing screenshots at {timestamp}...')

		for block in blocks:
			try:
				# Create filename with block name and timestamp
				filename = f'{block.name}_{timestamp_safe}.png'
				filepath = self.screenshot_dir / filename

				# Take screenshot using browser session
				screenshot_bytes = await self.browser_session.screenshot_element(
					selector=block.selector, path=str(filepath), format='png'
				)

				# Create metadata entry
				metadata = ScreenshotMetadata(
					timestamp=timestamp,
					block_name=block.name,
					screenshot_path=str(filepath.relative_to('.')),
					url=current_url,
				)

				self.metadata_list.append(metadata)
				print(f'  ✅ {block.name}: {filepath}')

			except Exception as e:
				print(f'  ❌ Failed to screenshot {block.name}: {e}')

		# Save metadata after each capture cycle
		self._save_metadata()
		print(f'✅ Screenshot cycle completed. Total screenshots: {len(self.metadata_list)}')

	async def _get_current_url(self) -> str:
		"""Get the current URL from browser session."""
		if not self.browser_session:
			return self.target_url

		try:
			state: BrowserState = await self.browser_session.get_state()
			return state.url
		except Exception:
			return self.target_url

	async def run_monitoring_loop(self) -> None:
		"""
		Main monitoring loop that periodically captures screenshots.
		"""
		print('\n' + '=' * 60)
		print('🚀 STARTING SCHEDULED SCREENSHOT MONITORING')
		print('=' * 60)
		print(f'Target URL: {self.target_url}')
		print(f'Interval: {self.interval_seconds} seconds ({self.interval_seconds / 60:.1f} minutes)')
		print(f'Screenshot directory: {self.screenshot_dir}')
		print(f'Metadata file: {self.metadata_file}')
		print('=' * 60 + '\n')

		# Step 1: Wait for user to login
		login_success = await self.wait_for_login()
		if not login_success:
			print('❌ Login failed or was cancelled')
			return

		# Step 2: Identify chart blocks once
		blocks = await self.identify_chart_blocks()
		if not blocks:
			print('❌ No chart blocks found. Exiting.')
			return

		# Step 3: Start monitoring loop
		cycle = 1
		try:
			while True:
				print(f'\n{"=" * 60}')
				print(f'📊 SCREENSHOT CYCLE #{cycle}')
				print(f'{"=" * 60}')

				# Refresh the page to get latest data
				await self.browser_session.goto(self.target_url)
				await asyncio.sleep(3)  # Wait for page to load

				# Capture screenshots
				await self.capture_block_screenshots(blocks)

				# Wait for next cycle
				print(f'\n⏳ Next screenshot in {self.interval_seconds} seconds...')
				print(f'   (Press Ctrl+C to stop monitoring)\n')

				await asyncio.sleep(self.interval_seconds)
				cycle += 1

		except KeyboardInterrupt:
			print('\n\n🛑 Monitoring stopped by user')
		except Exception as e:
			print(f'\n\n❌ Error in monitoring loop: {e}')
		finally:
			# Final save of metadata
			self._save_metadata()
			print(f'\n✅ Total screenshots captured: {len(self.metadata_list)}')
			print(f'📁 Screenshots saved in: {self.screenshot_dir}')
			print(f'📄 Metadata saved in: {self.metadata_file}')

			# Close browser
			if self.browser_session:
				await self.browser_session.close()


async def main():
	"""Main entry point for the scheduled screenshot monitor."""
	import argparse

	parser = argparse.ArgumentParser(description='Scheduled Screenshot Monitoring System')
	parser.add_argument('--url', type=str, required=True, help='Target URL to monitor')
	parser.add_argument(
		'--interval', type=int, default=300, help='Screenshot interval in seconds (default: 300 = 5 minutes)'
	)
	parser.add_argument('--screenshot-dir', type=str, default='screenshots', help='Directory to save screenshots')
	parser.add_argument(
		'--metadata-file', type=str, default='screenshot_metadata.json', help='JSON file for metadata'
	)

	args = parser.parse_args()

	# Create and run monitor
	monitor = ScheduledScreenshotMonitor(
		target_url=args.url,
		screenshot_dir=args.screenshot_dir,
		metadata_file=args.metadata_file,
		interval_seconds=args.interval,
	)

	await monitor.run_monitoring_loop()


if __name__ == '__main__':
	asyncio.run(main())
