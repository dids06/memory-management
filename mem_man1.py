import tkinter as tk
from tkinter import ttk, messagebox

class Allocator:
    def __init__(self):
        self.cells = []  
        self.blocks = []  
        self.proc_sizes = []

    def init_memory(self, cell_sizes):
        self.cells = []
        self.blocks = []
        pos = 0
        for i, sz in enumerate(cell_sizes, start=1):
            self.cells.append({"id": i, "start": pos, "size": sz})
            self.blocks.append({"start": pos, "size": sz, "pid": None, "cell_id": i})
            pos += sz

    def init_processes(self, sizes):
        self.proc_sizes = sizes


    def _free_blocks(self, need=None):
        blks = [b for b in self.blocks if b["pid"] is None]
        if need is not None:
            blks = [b for b in blks if b["size"] >= need]
        return blks

    def _pick_block(self, need, strategy):
        cands = self._free_blocks(need)
        if not cands:
            return None
        if strategy == "First Fit":
            return min(cands, key=lambda b: b["start"])
        if strategy == "Best Fit":
            return min(cands, key=lambda b: b["size"])
        return max(cands, key=lambda b: b["size"])

    def allocate_all(self, strategy):
        """Allocates P1..Pn in order. Returns [(pindex, need, start_or_None, got_size_or_0)]."""
        results = []
        for idx, need in enumerate(self.proc_sizes, start=1):
            blk = self._pick_block(need, strategy)
            if not blk:
                results.append((idx, need, None, 0))
                continue
            i = self.blocks.index(blk)
            if blk["size"] == need:
                blk["pid"] = idx
                results.append((idx, need, blk["start"], blk["size"]))
            else:
                a = {"start": blk["start"], "size": need, "pid": idx, "cell_id": blk["cell_id"]}
                r = {"start": blk["start"] + need, "size": blk["size"] - need, "pid": None, "cell_id": blk["cell_id"]}
                self.blocks[i:i+1] = [a, r]
                results.append((idx, need, a["start"], a["size"]))
        return results

    def cell_summary(self):
        """Per-cell view for the UI: [{'cell':i,'size':S,'remaining':R,'procs':[1,3,...]}]"""
        out = []
        self.blocks.sort(key=lambda b: b["start"])
        for cell in self.cells:
            cid = cell["id"]
            size = cell["size"]
            blks = [b for b in self.blocks if b["cell_id"] == cid]
            remaining = sum(b["size"] for b in blks if b["pid"] is None)
            procs = [b["pid"] for b in blks if b["pid"] is not None]
            out.append({"cell": cid, "size": size, "remaining": remaining, "procs": procs})
        return out

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Memory Allocation (First / Best / Worst Fit)")
        self.geometry("1120x720")
        self.alloc = Allocator()
        self.strategy = tk.StringVar(value="First Fit")
        self.scale_px = tk.DoubleVar(value=0.6)

        self._build()
    def _build(self):
        top = ttk.Frame(self, padding=8)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Process sizes:").grid(row=0, column=0, sticky="w")
        self.proc_entry = ttk.Entry(top, width=55)
        self.proc_entry.grid(row=0, column=1, padx=8, sticky="w")
        ttk.Label(top, text="(e.g. 90,30,55,20)").grid(row=0, column=2, sticky="w")

        ttk.Label(top, text="Memory cell sizes:").grid(row=1, column=0, sticky="w", pady=(6,0))
        self.cell_entry = ttk.Entry(top, width=55)
        self.cell_entry.grid(row=1, column=1, padx=8, pady=(6,0), sticky="w")
        ttk.Label(top, text="(e.g. 100,64,128,32)").grid(row=1, column=2, sticky="w", pady=(6,0))

        opts = ttk.Frame(top)
        opts.grid(row=0, column=3, rowspan=2, padx=(16,0), sticky="n")
        ttk.Label(opts, text="Algorithm:").grid(row=0, column=0, sticky="w")
        for i, name in enumerate(["First Fit","Best Fit","Worst Fit"], start=1):
            ttk.Radiobutton(opts, text=name, value=name, variable=self.strategy).grid(row=i, column=0, sticky="w")
        ttk.Label(opts, text="Pixels per unit:").grid(row=4, column=0, pady=(8,0), sticky="w")
        ttk.Spinbox(opts, from_=0.1, to=6.0, increment=0.1, textvariable=self.scale_px, width=6,
                    command=self.redraw).grid(row=5, column=0, sticky="w")

        runbar = ttk.Frame(self, padding=8)
        runbar.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(runbar, text="Run Allocation", command=self.run_allocation).pack(side=tk.LEFT)
        ttk.Button(runbar, text="Reset", command=self.reset_all).pack(side=tk.LEFT, padx=8)

        body = ttk.Frame(self, padding=(8,0,8,8))
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,8))
        self.canvas = tk.Canvas(left, background="#ffffff", highlightthickness=1,
                                highlightbackground="#cfcfcf", height=420)
        self.vscroll = ttk.Scrollbar(left, orient="vertical", command=self.canvas.yview)
        self.hscroll = ttk.Scrollbar(left, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.hscroll.set, yscrollcommand=self.vscroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vscroll.grid(row=0, column=1, sticky="ns")
        self.hscroll.grid(row=1, column=0, sticky="ew")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        right = ttk.Frame(body, width=380)
        right.pack(side=tk.LEFT, fill=tk.BOTH)

        table_box = ttk.LabelFrame(right, text="Process results")
        table_box.pack(fill=tk.BOTH, expand=True, pady=(0,8))
        self.tree = ttk.Treeview(table_box, columns=("proc","need","start","end","alloc"),
                                 show="headings", height=12)
        self.tree.heading("proc", text="Process")
        self.tree.heading("need", text="Size")
        self.tree.heading("start", text="Start address")
        self.tree.heading("end", text="End address")
        self.tree.heading("alloc", text="Allocated")
        self.tree.column("proc", width=90, anchor="center")
        self.tree.column("need", width=80, anchor="center")
        self.tree.column("start", width=100, anchor="center")
        self.tree.column("end", width=100, anchor="center")
        self.tree.column("alloc", width=90, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        cells_box = ttk.LabelFrame(right, text="Memory cells (remaining after allocation)")
        cells_box.pack(fill=tk.BOTH, expand=False)
        self.cells_tree = ttk.Treeview(cells_box, columns=("cell","size","remain"),
                                       show="headings", height=6)
        self.cells_tree.heading("cell", text="Cell")
        self.cells_tree.heading("size", text="Size")
        self.cells_tree.heading("remain", text="Remaining")
        self.cells_tree.column("cell", width=60, anchor="center")
        self.cells_tree.column("size", width=90, anchor="center")
        self.cells_tree.column("remain", width=110, anchor="center")
        self.cells_tree.pack(fill=tk.X, expand=False, padx=6, pady=6)

        self.status = tk.StringVar(value="Enter process sizes and memory cell sizes, choose algorithm, then Run.")
        ttk.Label(self, textvariable=self.status, anchor="w", padding=8).pack(fill=tk.X)

        self.bind("<Configure>", lambda e: self.redraw())

    def parse_int_list(self, text):
        parts = [p for p in text.replace(" ","").split(",") if p!=""]
        vals = [int(x) for x in parts]
        if not vals or any(v<=0 for v in vals):
            raise ValueError
        return vals

    def run_allocation(self):
        try:
            proc_sizes = self.parse_int_list(self.proc_entry.get().strip())
            cell_sizes = self.parse_int_list(self.cell_entry.get().strip())
        except:
            messagebox.showerror("Invalid Input", "Use comma-separated positive integers for both lists.")
            return

        self.alloc.init_memory(cell_sizes)
        self.alloc.init_processes(proc_sizes)

        for i in self.tree.get_children():
            self.tree.delete(i)
        results = self.alloc.allocate_all(self.strategy.get())
        for (p, need, start, got) in results:
            if start is None or got == 0:
                start_val = "-"
                end_val = "-"
                alloc_val = "No"
            else:
                start_val = start
                end_val = start + got
                alloc_val = got
            self.tree.insert("", tk.END,
                             values=(f"P{p}", need, start_val, end_val, alloc_val))

        for i in self.cells_tree.get_children():
            self.cells_tree.delete(i)
        for info in self.alloc.cell_summary():
            self.cells_tree.insert("", tk.END, values=(f"Cell {info['cell']}", info["size"], info["remaining"]))

        total = sum(cell_sizes)
        placed = sum(got for (_,_,_,got) in results)
        self.status.set(f"Placed {len([1 for r in results if r[3]>0])}/{len(results)} processes. Used {placed}/{total} units.")
        self.redraw()

    def reset_all(self):
        self.proc_entry.delete(0, tk.END)
        self.cell_entry.delete(0, tk.END)
        for i in self.tree.get_children():
            self.tree.delete(i)
        for i in self.cells_tree.get_children():
            self.cells_tree.delete(i)
        self.alloc = Allocator()
        self.canvas.delete("all")
        self.status.set("Cleared. Enter new inputs and Run.")

    def redraw(self):
        """Draw original cells only (single lines) and write the processes placed in each cell."""
        self.canvas.delete("all")
        cells = getattr(self.alloc, "cells", [])
        if not cells:
            self.canvas.configure(scrollregion=(0,0,0,0))
            return

        px = max(0.1, float(self.scale_px.get()))
        x0, y0, h = 40, 80, 120
        outline = "#000000"

        total_units = sum(c["size"] for c in cells)
        total_w = max(1, int(total_units * px))
        self.canvas.create_rectangle(x0, y0, x0 + total_w, y0 + h, outline=outline, fill="")

        x = x0
        summaries = {d["cell"]: d for d in self.alloc.cell_summary()}
        for c in cells:
            w = max(1, int(c["size"] * px))
            if x > x0:
                self.canvas.create_line(x, y0, x, y0 + h, fill=outline)

            info = summaries.get(c["id"], {"procs": [], "remaining": c["size"]})
            procs = info["procs"]
            label = ", ".join(f"P{p}" for p in procs) if procs else "free"
            self.canvas.create_text(x + w/2, y0 + h/2, text=label, font=("Segoe UI", 11))
            x += w

        self.canvas.configure(scrollregion=(0, 0, x + 60, y0 + h + 120))

if __name__ == "__main__":
    App().mainloop()
