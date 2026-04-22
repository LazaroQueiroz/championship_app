import time
import threading
import sys

stop_event = threading.Event()
time_up_event = threading.Event()
remaining = {"seconds": 5}
state = {"is_idle": False}

def timer_thread() -> None:
    while remaining["seconds"] > 0 and not stop_event.is_set():
        if state["is_idle"]:
            mins = remaining["seconds"] // 60
            secs = remaining["seconds"] % 60
            sys.stdout.write(f"\033[s\033[1A\r\033[2K⏱️  Tempo restante: {mins:02d}:{secs:02d}\033[u")
            sys.stdout.flush()
        time.sleep(1)
        remaining["seconds"] -= 1

    if not stop_event.is_set():
        time_up_event.set()
        print("\nTempo encerrado!")

print("Partida iniciada!")
t = threading.Thread(target=timer_thread, daemon=True)
t.start()

while not time_up_event.is_set():
    state["is_idle"] = False
    print()
    state["is_idle"] = True
    try:
        cmd = input("Comando: ").strip().lower()
    except EOFError:
        break
    state["is_idle"] = False
    print(f"Executou: {cmd}")
    if cmd == "fim":
        stop_event.set()
        break

stop_event.set()
t.join()
