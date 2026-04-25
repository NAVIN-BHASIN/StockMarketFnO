with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'self.grid_rowconfigure(2, weight=1)' in line:
        # Verify it's inside HedgeFundEngineFrame
        # Searching backwards for the class definition
        found_class = False
        for j in range(i, i - 20, -1):
            if 'class HedgeFundEngineFrame' in lines[j]:
                found_class = True
                break
        if found_class:
            print(f"Found target line at {i+1}, patching...")
            lines[i] = line.replace('rowconfigure(2', 'rowconfigure(1')
            break

with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Done")
