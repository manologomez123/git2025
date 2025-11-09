from __future__ import annotations

import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import List, TypedDict

import tkinter as tk
from tkinter import messagebox, simpledialog


SCORE_FILE = Path(__file__).with_name("fastsim_scores.json")
TOTAL_TARGET_CLICKS = 10
TARGET_RADIUS = 14
MAX_SCORES = 10


class ScoreEntry(TypedDict):
	name: str
	time: float
	timestamp: str


class FastClickGame:
	def __init__(self, root: tk.Tk) -> None:
		self.root = root
		self.root.title("FastSim - Click Challenge")
		self.root.resizable(False, False)

		self.canvas_size = 500

		main_frame = tk.Frame(root, padx=12, pady=12)
		main_frame.pack()

		header = tk.Label(
			main_frame,
			text="¡Haz clic en el punto lo más rápido posible!",
			font=("Segoe UI", 14, "bold"),
		)
		header.pack(pady=(0, 8))

		self.canvas = tk.Canvas(
			main_frame,
			width=self.canvas_size,
			height=self.canvas_size,
			bg="black",
			highlightthickness=0,
		)
		self.canvas.pack()

		info_frame = tk.Frame(main_frame)
		info_frame.pack(fill="x", pady=8)

		self.status_label = tk.Label(info_frame, text="Clicks: 0 / 10", font=("Segoe UI", 10))
		self.status_label.pack(side=tk.LEFT)

		self.timer_label = tk.Label(info_frame, text="Tiempo: 0.000 s", font=("Segoe UI", 10))
		self.timer_label.pack(side=tk.LEFT, padx=16)

		self.best_label = tk.Label(info_frame, text="Mejor tiempo: --", font=("Segoe UI", 10, "italic"))
		self.best_label.pack(side=tk.LEFT)

		self.score_label = tk.Label(
			main_frame,
			text="",
			font=("Consolas", 10),
			justify=tk.LEFT,
			anchor="w",
		)
		self.score_label.pack(fill="x", pady=(8, 0))

		button_frame = tk.Frame(main_frame)
		button_frame.pack(fill="x", pady=(8, 0))

		self.play_button = tk.Button(button_frame, text="Empezar", command=self.start_countdown)
		self.play_button.pack(side=tk.LEFT)

		self.reset_scores_button = tk.Button(
			button_frame,
			text="Reset high scores",
			command=self.reset_scores,
		)
		self.reset_scores_button.pack(side=tk.LEFT, padx=6)

		self.scores: List[ScoreEntry] = self.load_scores()
		self.player_name: str | None = None

		self.target_id = self.canvas.create_oval(0, 0, 0, 0, fill="#ff4d4d", outline="")
		self.canvas.tag_bind(self.target_id, "<Button-1>", self.on_target_click)

		self.hits = 0
		self.start_time: float | None = None
		self.game_active = False
		self.countdown_value = 0

		self.countdown_label = tk.Label(main_frame, text="", font=("Segoe UI", 32, "bold"))
		self.countdown_label.pack(pady=(12, 0))

		self.update_scoreboard()
		self.prepare_game()

	# ------------------------------------------------------------------
	#  Persistence helpers
	# ------------------------------------------------------------------
	def load_scores(self) -> List[ScoreEntry]:
		if not SCORE_FILE.exists():
			return []

		try:
			with SCORE_FILE.open("r", encoding="utf-8") as fh:
				data = json.load(fh)
			if isinstance(data, list):
				valid_scores: List[ScoreEntry] = []
				for item in data:
					if (
						isinstance(item, dict)
						and isinstance(item.get("name"), str)
						and isinstance(item.get("time"), (int, float))
						and isinstance(item.get("timestamp"), str)
					):
						valid_scores.append(
							ScoreEntry(
								name=item["name"],
								time=float(item["time"]),
								timestamp=item["timestamp"],
							)
						)
				return sorted(valid_scores, key=lambda s: s["time"])[:MAX_SCORES]
		except (OSError, json.JSONDecodeError):
			pass

		return []

	def save_scores(self) -> None:
		try:
			with SCORE_FILE.open("w", encoding="utf-8") as fh:
				json.dump(self.scores, fh, ensure_ascii=False, indent=2)
		except OSError as exc:
			messagebox.showwarning("FastSim", f"No se pudieron guardar los high scores: {exc}")

	# ------------------------------------------------------------------
	#  Game flow
	# ------------------------------------------------------------------
	def prepare_game(self) -> None:
		"""Resetear estado sin iniciar todavía."""
		self.hits = 0
		self.start_time = None
		self.game_active = False
		self.status_label.config(text=f"Clicks: {self.hits} / {TOTAL_TARGET_CLICKS}")
		self.timer_label.config(text="Tiempo: 0.000 s")
		self.countdown_label.config(text="")
		self.play_button.config(text="Empezar")

		best_time = self.scores[0]["time"] if self.scores else None
		if best_time is None:
			self.best_label.config(text="Mejor tiempo: --")
		else:
			self.best_label.config(text=f"Mejor tiempo: {best_time:.3f} s")

		self.canvas.itemconfig(self.target_id, state="hidden")
		self.update_scoreboard()

	def start_countdown(self) -> None:
		if self.game_active:
			return

		self.prepare_game()
		self.play_button.config(state=tk.DISABLED)
		self.countdown_value = 3
		self.countdown_label.config(text=str(self.countdown_value))
		self.root.after(1000, self._tick_countdown)

	def _tick_countdown(self) -> None:
		self.countdown_value -= 1
		if self.countdown_value == 0:
			self.countdown_label.config(text="¡Ya!")
			self.root.after(500, self._start_game)
		else:
			self.countdown_label.config(text=str(self.countdown_value))
			self.root.after(1000, self._tick_countdown)

	def _start_game(self) -> None:
		self.countdown_label.config(text="")
		self.game_active = True
		self.move_target(initial=True)
		self.play_button.config(state=tk.NORMAL, text="Reiniciar", command=self.start_countdown)

	def on_target_click(self, _event: tk.Event) -> None:
		if not self.game_active:
			return

		if self.start_time is None:
			self.start_time = time.perf_counter()

		self.hits += 1
		self.status_label.config(text=f"Clicks: {self.hits} / {TOTAL_TARGET_CLICKS}")

		if self.start_time is not None:
			elapsed = time.perf_counter() - self.start_time
			self.timer_label.config(text=f"Tiempo: {elapsed:.3f} s")

		if self.hits >= TOTAL_TARGET_CLICKS:
			self.finish_game()
		else:
			self.move_target()

	def move_target(self, *, initial: bool = False) -> None:
		padding = TARGET_RADIUS + 4
		x = random.randint(padding, self.canvas_size - padding)
		y = random.randint(padding, self.canvas_size - padding)
		self.canvas.coords(
			self.target_id,
			x - TARGET_RADIUS,
			y - TARGET_RADIUS,
			x + TARGET_RADIUS,
			y + TARGET_RADIUS,
		)
		if initial:
			self.canvas.itemconfig(self.target_id, state="normal")

	def finish_game(self) -> None:
		self.game_active = False
		self.canvas.itemconfig(self.target_id, state="hidden")

		if self.start_time is None:
			return

		elapsed = time.perf_counter() - self.start_time
		self.timer_label.config(text=f"Tiempo: {elapsed:.3f} s")

		messagebox.showinfo("FastSim", f"¡Reto completado en {elapsed:.3f} segundos!")
		self.record_score(elapsed)

	# ------------------------------------------------------------------
	#  Scores
	# ------------------------------------------------------------------
	def record_score(self, elapsed: float) -> None:
		if not self.player_name:
			name = simpledialog.askstring("FastSim", "¿Cuál es tu nombre?", parent=self.root)
			self.player_name = name.strip() if name else "Anónimo"

		score = ScoreEntry(
			name=self.player_name or "Anónimo",
			time=elapsed,
			timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
		)

		self.scores.append(score)
		self.scores.sort(key=lambda s: s["time"])
		self.scores = self.scores[:MAX_SCORES]
		self.save_scores()
		self.update_scoreboard()

	def reset_scores(self) -> None:
		if not messagebox.askyesno("FastSim", "¿Seguro que deseas borrar todos los high scores?"):
			return
		self.scores = []
		if SCORE_FILE.exists():
			try:
				SCORE_FILE.unlink()
			except OSError:
				pass
		self.update_scoreboard()
		self.best_label.config(text="Mejor tiempo: --")

	def update_scoreboard(self) -> None:
		if not self.scores:
			text = "High Scores:\n  (sin registros)"
		else:
			lines = ["High Scores:"]
			for idx, entry in enumerate(self.scores, start=1):
				lines.append(
					f" {idx:>2}. {entry['name'][:12]:<12} {entry['time']:.3f} s   {entry['timestamp']}"
				)
			text = "\n".join(lines)
		self.score_label.config(text=text)


def main() -> None:
	root = tk.Tk()
	FastClickGame(root)
	root.mainloop()


if __name__ == "__main__":
	main()
