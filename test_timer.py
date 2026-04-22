import time
import threading

stop_event = threading.Event()
remaining = {"seconds": 15}

def timer_thread() -> None:
    while remaining["seconds"] > 0 and not stop_event.is_set():
        mins = remaining["seconds"] // 60
        secs = remaining["seconds"] % 60
        # save, up 1, erase line, write time, restore
        print(f"\033[s\033[1A\r\033[2K⏱️  Tempo restante: {mins:02d}:{secs:02d}\033[u", end="", flush=True)
        time.sleep(1)
        remaining["seconds"] -= 1

    if not stop_event.is_set():
        print("\nTempo encerrado!")

print("Partida iniciada!")
print() # Print empty line for the timer to land on
t = threading.Thread(target=timer_thread, daemon=True)
t.start()

while remaining["seconds"] > 0:
    cmd = input("Comando: ")
    print(f"Executando {cmd}...")
    if cmd == "fim":
        stop_event.set()
        break
    print() # give a new empty line for the timer

