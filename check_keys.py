import keyboard

print("Press keys to see their names. Ctrl+C to quit.")
keyboard.hook(lambda e: print(f"{e.event_type:8} scan={e.scan_code:5} name={e.name!r}"))
keyboard.wait()
