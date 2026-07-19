import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import tkinter.ttk as ttk
from PIL import Image, ImageDraw
from datetime import datetime
import os

class YokogawaArchitectureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Yokogawa System Architecture Builder (ISA/IEC 62443)")
        self.root.geometry("1450x1100")
        self.root.configure(bg="#ffffff")

        # System structure: {level_key: {equipment_name: {instance_id: {name, type, properties}}}}
        self.systems = {
            'l4': {},
            'dmz': {},
            'l3': {},
            'l2': {},
            'l1': {}
        }
        
        # Counter for auto-generated names
        self.instance_counters = {}
        self.selected_system = None  # Track selected system for editing
        self.system_positions = {}   # Track system positions for click detection
        
        self.l3_has_switch = False
        self.l2_has_switch = False

        # --- Top Toolbar ---
        toolbar_frame = tk.Frame(self.root, bg="#f0f0f0", relief=tk.RAISED, bd=1)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        tk.Button(toolbar_frame, text="📥 Export as Image", bg="#4CAF50", fg="white", 
                 font=("Segoe UI", 9, "bold"), command=self.export_as_image).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar_frame, text="🔄 Reset All", bg="#FF9800", fg="white",
                 font=("Segoe UI", 9, "bold"), command=self.reset_architecture).pack(side=tk.LEFT, padx=5)
        
        # --- Layout Setup ---
        # Left Pane with Scrollbar (Compact width)
        self.left_pane_frame = tk.Frame(self.root, relief=tk.RIDGE, bd=2, bg="#f8f9fa")
        self.left_pane_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        self.left_pane_canvas = tk.Canvas(self.left_pane_frame, bg="#f8f9fa", highlightthickness=0, width=280)
        self.left_pane_scrollbar = ttk.Scrollbar(self.left_pane_frame, orient=tk.VERTICAL, command=self.left_pane_canvas.yview)
        self.left_pane_scrollable = tk.Frame(self.left_pane_canvas, bg="#f8f9fa", padx=12, pady=10)
        
        self.left_pane_scrollable.bind(
            "<Configure>",
            lambda e: self.left_pane_canvas.configure(scrollregion=self.left_pane_canvas.bbox("all"))
        )
        
        self.left_pane_canvas.create_window((0, 0), window=self.left_pane_scrollable, anchor="nw")
        self.left_pane_canvas.configure(yscrollcommand=self.left_pane_scrollbar.set)
        self.left_pane_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.left_pane_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind mousewheel to left pane
        self.left_pane_canvas.bind("<MouseWheel>", lambda e: self._scroll_left_pane(e))
        self.left_pane_canvas.bind("<Button-4>", lambda e: self.left_pane_canvas.yview_scroll(-1, "units"))
        self.left_pane_canvas.bind("<Button-5>", lambda e: self.left_pane_canvas.yview_scroll(1, "units"))
        self.left_pane_scrollable.bind("<MouseWheel>", lambda e: self._scroll_left_pane(e))

        # Right side container with canvas and edit panel
        right_container = tk.Frame(self.root, bg="#ffffff")
        right_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas Frame with Scrollbars
        self.canvas_frame = tk.Frame(right_container, bg="#ffffff", relief=tk.RIDGE, bd=2)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#ffffff", highlightthickness=0, cursor="crosshair")
        self.canvas_scrollbar_y = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas_scrollbar_x = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=self.canvas_scrollbar_y.set, xscrollcommand=self.canvas_scrollbar_x.set)
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas_scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.canvas_scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Bind mousewheel to canvas
        self.canvas.bind("<MouseWheel>", lambda e: self._scroll_canvas(e))
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        self.canvas.bind("<Configure>", self.on_resize)
        
        # Edit Panel (collapsible)
        self.edit_panel_frame = tk.LabelFrame(right_container, text="Edit System", bg="#f5f5f5", font=("Segoe UI", 9, "bold"))
        self.edit_panel_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.edit_system_name = tk.StringVar()
        self.edit_system_type = tk.StringVar()
        self.edit_system_props = tk.StringVar()
        
        # Name field
        tk.Label(self.edit_panel_frame, text="System Name:", bg="#f5f5f5", font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(5, 0))
        name_entry = tk.Entry(self.edit_panel_frame, textvariable=self.edit_system_name, font=("Segoe UI", 8))
        name_entry.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        # Type field
        tk.Label(self.edit_panel_frame, text="Type:", bg="#f5f5f5", font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(5, 0))
        type_entry = tk.Entry(self.edit_panel_frame, textvariable=self.edit_system_type, font=("Segoe UI", 8))
        type_entry.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        # Properties field
        tk.Label(self.edit_panel_frame, text="Properties (optional):", bg="#f5f5f5", font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(5, 0))
        props_entry = tk.Entry(self.edit_panel_frame, textvariable=self.edit_system_props, font=("Segoe UI", 8))
        props_entry.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        # Buttons
        btn_frame = tk.Frame(self.edit_panel_frame, bg="#f5f5f5")
        btn_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        tk.Button(btn_frame, text="💾 Save", bg="#2196F3", fg="white", font=("Segoe UI", 8),
                 command=self.save_system_edit).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🗑️ Delete", bg="#f44336", fg="white", font=("Segoe UI", 8),
                 command=self.delete_selected_system).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="❌ Clear", bg="#999999", fg="white", font=("Segoe UI", 8),
                 command=self.clear_selection).pack(side=tk.LEFT, padx=5)
        
        self.edit_panel_frame.pack_forget()  # Hide initially
        
        self.setup_ui()

    def _scroll_left_pane(self, event):
        """Handle mousewheel for left pane"""
        self.left_pane_canvas.yview_scroll(-1*(event.delta//120), "units")

    def _scroll_canvas(self, event):
        """Handle mousewheel for canvas"""
        self.canvas.yview_scroll(-1*(event.delta//120), "units")

    def setup_ui(self):
        def create_section(title, equipment_list, level_key):
            section_frame = tk.Frame(self.left_pane_scrollable, bg="#f8f9fa")
            section_frame.pack(fill=tk.X, pady=(12, 5))
            
            tk.Label(section_frame, text=title, bg="#f8f9fa", fg="#000000", 
                     font=("Segoe UI", 8, "bold")).pack(pady=(5, 5), anchor="w")
            
            for equipment in equipment_list:
                equipment_frame = tk.Frame(section_frame, bg="#f8f9fa")
                equipment_frame.pack(fill=tk.X, pady=1)
                
                if equipment == "L3 Managed Switch":
                    btn = tk.Button(equipment_frame, text=f"+ Add {equipment}", bg="#ffffff", fg="#000000",
                                    font=("Segoe UI", 7), relief=tk.SOLID, bd=1, pady=2,
                                    command=self.toggle_l3_switch)
                    btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
                    
                elif equipment == "L2 Network Switches":
                    btn = tk.Button(equipment_frame, text=f"+ Add {equipment}", bg="#ffffff", fg="#000000",
                                    font=("Segoe UI", 7), relief=tk.SOLID, bd=1, pady=2,
                                    command=self.toggle_l2_switch)
                    btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
                    
                else:
                    # Add button for equipment - AUTO ADD
                    btn = tk.Button(equipment_frame, text=f"+ {equipment}", bg="#ffffff", fg="#000000",
                                    font=("Segoe UI", 7), relief=tk.SOLID, bd=1, pady=2,
                                    command=lambda e=equipment, lk=level_key: self.auto_add_equipment(e, lk))
                    btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
                    
                    # View/Manage button
                    view_btn = tk.Button(equipment_frame, text="View", bg="#e9ecef", fg="#000000",
                                        font=("Segoe UI", 7), relief=tk.SOLID, bd=1, pady=2, width=4,
                                        command=lambda e=equipment, lk=level_key: self.show_equipment_instances(e, lk))
                    view_btn.pack(side=tk.LEFT)
                
                # Instance counter label
                counter_label = tk.Label(equipment_frame, text="", bg="#f8f9fa", fg="#666666",
                                        font=("Segoe UI", 6, "italic"))
                counter_label.pack(side=tk.LEFT, padx=3)
                
                # Store reference to update counter
                if equipment not in ["L3 Managed Switch", "L2 Network Switches"]:
                    if not hasattr(self, 'counters'):
                        self.counters = {}
                    self.counters[f"{level_key}_{equipment}"] = counter_label

        # --- Populate Left Pane Controls ---
        create_section("LEVEL 4: ENTERPRISE ZONE", 
                       ["ERP Server", "Corporate AD"], 
                       'l4')
                       
        create_section("LEVEL 3.5: DMZ", 
                       ["Web/Report Server", "Patch Server (WSUS)", "Jump Host"], 
                       'dmz')
                       
        create_section("LEVEL 3: OPERATIONS SUPPORT", 
                       ["L3 Managed Switch", "Domain Controller (AD)", "Exa-Quantum PIMS", "NAS Storage", "SIEM / Syslog", "AV Server"], 
                       'l3')
                       
        create_section("LEVEL 2: CONTROL NETWORK", 
                       ["L2 Network Switches", "OWS", "EWS", "SENG", "EXA-OPC"], 
                       'l2')

        # Level 1 Controllers Section
        l1_frame = tk.Frame(self.left_pane_scrollable, bg="#e8f4f8", relief=tk.SUNKEN, bd=2, padx=10, pady=8)
        l1_frame.pack(fill=tk.X, pady=(12, 5))
        
        tk.Label(l1_frame, text="LEVEL 1: FIELD", bg="#e8f4f8", fg="#000000",
                font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 5))
        
        l1_equipment = ["F&G (Fire & Gas)", "SCS (Safety Control)", "FCS (Field Control)"]
        
        self.l1_counters = {}
        
        for equipment in l1_equipment:
            l1_eq_frame = tk.Frame(l1_frame, bg="#e8f4f8")
            l1_eq_frame.pack(fill=tk.X, pady=1)
            
            btn = tk.Button(l1_eq_frame, text=f"+ {equipment}", bg="#ffffff", fg="#000000",
                            font=("Segoe UI", 7), relief=tk.SOLID, bd=1, pady=2,
                            command=lambda e=equipment, lk='l1': self.auto_add_equipment(e, lk))
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
            
            view_btn = tk.Button(l1_eq_frame, text="View", bg="#e9ecef", fg="#000000",
                                font=("Segoe UI", 7), relief=tk.SOLID, bd=1, pady=2, width=4,
                                command=lambda e=equipment, lk='l1': self.show_equipment_instances(e, lk))
            view_btn.pack(side=tk.LEFT)
            
            counter_label = tk.Label(l1_eq_frame, text="", bg="#e8f4f8", fg="#666666",
                                    font=("Segoe UI", 6, "italic"))
            counter_label.pack(side=tk.LEFT, padx=3)
            
            self.l1_counters[f"l1_{equipment}"] = counter_label

        # Instructions
        instr_frame = tk.Frame(self.left_pane_scrollable, bg="#f8f9fa", pady=10)
        instr_frame.pack(fill=tk.X, pady=(15, 5))
        
        tk.Label(instr_frame, text="📋 Instructions:", bg="#f8f9fa", fg="#333333",
                font=("Segoe UI", 7, "bold")).pack(anchor="w")
        tk.Label(instr_frame, text="• Click + to add instance\n• Click system to edit\n• Click View to manage\n• Export diagram as image",
                bg="#f8f9fa", fg="#555555", font=("Segoe UI", 6), justify=tk.LEFT).pack(anchor="w", padx=(5, 0))

    def auto_add_equipment(self, equipment_name, level_key):
        """Auto-add equipment with generated name"""
        # Generate auto name
        counter_key = f"{level_key}_{equipment_name}"
        if counter_key not in self.instance_counters:
            self.instance_counters[counter_key] = 0
        
        self.instance_counters[counter_key] += 1
        
        # Extract short name from equipment
        short_name = equipment_name.split('(')[0].strip().split()[0]
        instance_name = f"{short_name}-{self.instance_counters[counter_key]}"
        
        # Initialize equipment dict if not exists
        if equipment_name not in self.systems[level_key]:
            self.systems[level_key][equipment_name] = {}
        
        # Create instance ID
        instance_id = len(self.systems[level_key][equipment_name])
        
        # Add instance
        self.systems[level_key][equipment_name][instance_id] = {
            'name': instance_name,
            'type': equipment_name,
            'properties': ''
        }
        
        # Update counter
        if level_key == 'l1':
            if counter_key in self.l1_counters:
                count = len(self.systems[level_key][equipment_name])
                self.l1_counters[counter_key].config(text=f"({count})")
        else:
            if counter_key in self.counters:
                count = len(self.systems[level_key][equipment_name])
                self.counters[counter_key].config(text=f"({count})")
        
        self.draw_architecture()

    def show_equipment_instances(self, equipment_name, level_key):
        """Show and manage instances of equipment"""
        instances = self.systems[level_key].get(equipment_name, {})
        
        # Create popup window
        popup = tk.Toplevel(self.root)
        popup.title(f"Manage {equipment_name}")
        popup.geometry("400x300")
        
        tk.Label(popup, text=f"{equipment_name} Instances:", font=("Segoe UI", 10, "bold")).pack(pady=10)
        
        # Listbox with scrollbar
        frame = tk.Frame(popup)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        instance_list = []
        if not instances:
            listbox.insert(tk.END, "No instances added yet")
        else:
            for idx, (inst_id, data) in enumerate(instances.items()):
                instance_list.append((inst_id, data))
                listbox.insert(tk.END, f"{idx+1}. {data['name']}")
        
        # Button frame
        btn_frame = tk.Frame(popup)
        btn_frame.pack(pady=10)
        
        def remove_instance():
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                if instance_list:
                    inst_id = instance_list[idx][0]
                    del self.systems[level_key][equipment_name][inst_id]
                    
                    # Update counter
                    counter_key = f"{level_key}_{equipment_name}"
                    if level_key == 'l1':
                        if counter_key in self.l1_counters:
                            count = len(self.systems[level_key][equipment_name])
                            if count == 0:
                                self.l1_counters[counter_key].config(text="")
                            else:
                                self.l1_counters[counter_key].config(text=f"({count})")
                    else:
                        if counter_key in self.counters:
                            count = len(self.systems[level_key][equipment_name])
                            if count == 0:
                                self.counters[counter_key].config(text="")
                            else:
                                self.counters[counter_key].config(text=f"({count})")
                    
                    self.draw_architecture()
                    popup.destroy()
        
        tk.Button(btn_frame, text="Remove Selected", bg="#ff6b6b", fg="white", 
                 command=remove_instance).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", bg="#cccccc", 
                 command=popup.destroy).pack(side=tk.LEFT, padx=5)

    def on_canvas_click(self, event):
        """Handle clicks on canvas systems"""
        # Check if click is on a system
        for sys_id, (x1, y1, x2, y2, level_key, equipment, inst_id) in self.system_positions.items():
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.select_system(level_key, equipment, inst_id, sys_id)
                return

    def select_system(self, level_key, equipment, inst_id, sys_id):
        """Select a system for editing"""
        self.selected_system = (level_key, equipment, inst_id, sys_id)
        
        # Get system data
        system_data = self.systems[level_key][equipment][inst_id]
        
        # Update edit panel
        self.edit_system_name.set(system_data['name'])
        self.edit_system_type.set(system_data['type'])
        self.edit_system_props.set(system_data['properties'])
        
        # Show edit panel
        self.edit_panel_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Redraw to highlight selected
        self.draw_architecture()

    def save_system_edit(self):
        """Save edited system"""
        if not self.selected_system:
            messagebox.showwarning("Warning", "No system selected")
            return
        
        level_key, equipment, inst_id, _ = self.selected_system
        
        self.systems[level_key][equipment][inst_id] = {
            'name': self.edit_system_name.get(),
            'type': self.edit_system_type.get(),
            'properties': self.edit_system_props.get()
        }
        
        messagebox.showinfo("Success", "System updated successfully!")
        self.draw_architecture()

    def delete_selected_system(self):
        """Delete selected system"""
        if not self.selected_system:
            messagebox.showwarning("Warning", "No system selected")
            return
        
        if messagebox.askyesno("Confirm", "Delete this system?"):
            level_key, equipment, inst_id, _ = self.selected_system
            
            del self.systems[level_key][equipment][inst_id]
            
            # Update counter
            counter_key = f"{level_key}_{equipment}"
            if level_key == 'l1':
                if counter_key in self.l1_counters:
                    count = len(self.systems[level_key][equipment])
                    if count == 0:
                        self.l1_counters[counter_key].config(text="")
                    else:
                        self.l1_counters[counter_key].config(text=f"({count})")
            else:
                if counter_key in self.counters:
                    count = len(self.systems[level_key][equipment])
                    if count == 0:
                        self.counters[counter_key].config(text="")
                    else:
                        self.counters[counter_key].config(text=f"({count})")
            
            self.clear_selection()

    def clear_selection(self):
        """Clear selection"""
        self.selected_system = None
        self.edit_system_name.set("")
        self.edit_system_type.set("")
        self.edit_system_props.set("")
        self.edit_panel_frame.pack_forget()
        self.draw_architecture()

    def reset_architecture(self):
        """Reset all systems"""
        if messagebox.askyesno("Confirm", "Reset all systems? This cannot be undone."):
            self.systems = {'l4': {}, 'dmz': {}, 'l3': {}, 'l2': {}, 'l1': {}}
            self.instance_counters = {}
            self.l3_has_switch = False
            self.l2_has_switch = False
            self.clear_selection()

    def export_as_image(self):
        """Export architecture as image"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            initialfile=f"yokogawa_architecture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        
        if file_path:
            try:
                # Get canvas scroll region
                bbox = self.canvas.bbox("all")
                if not bbox:
                    messagebox.showwarning("Warning", "Nothing to export!")
                    return
                
                x1, y1, x2, y2 = bbox
                width = int(x2 - x1 + 20)
                height = int(y2 - y1 + 20)
                
                # Create PostScript output and convert to image
                ps = self.canvas.postscript(colormode='color')
                
                # For better compatibility, use tkinter's built-in method
                try:
                    from PIL import ImageGrab
                    # Get canvas coordinates on screen
                    bbox_screen = self.canvas.bbox("all")
                    if bbox_screen:
                        img = ImageGrab.grab(bbox=bbox_screen)
                        img.save(file_path)
                        messagebox.showinfo("Success", f"Image exported to:\n{file_path}")
                except:
                    messagebox.showwarning("Info", "Export requires PIL ImageGrab. Please ensure Pillow is installed with full support.")
            
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export image:\n{str(e)}")

    def on_resize(self, event):
        self.draw_architecture()
        
    def toggle_l3_switch(self):
        self.l3_has_switch = True
        self.draw_architecture()
        
    def toggle_l2_switch(self):
        self.l2_has_switch = True
        self.draw_architecture()

    def draw_architecture(self):
        self.canvas.delete("all")
        self.system_positions = {}
        
        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()

        if c_width < 100: c_width = 1800
        if c_height < 100: c_height = 1200

        # Calculate number of total systems for dynamic spacing
        total_l4 = len(self._flatten_instances(self.systems['l4']))
        total_dmz = len(self._flatten_instances(self.systems['dmz']))
        total_l3 = len(self._flatten_instances(self.systems['l3']))
        total_l2 = len(self._flatten_instances(self.systems['l2']))
        total_l1 = len(self._flatten_instances(self.systems['l1']))

        # Dynamic canvas height based on number of systems
        max_systems = max(total_l4, total_dmz, total_l3, total_l2)
        
        # Calculate spacing
        if max_systems > 5:
            canvas_height = 1200 + (max_systems - 5) * 150
        else:
            canvas_height = 1200

        # Y-Coordinates for Networks (Buses)
        l4_bus_y = 90
        dmz_bus_y = 180
        l3_bus_y = 270
        l2_pin_y = 360
        vnet1_y = 410
        vnet2_y = 460

        # --- 1. Draw Networks (Conduits) ---
        self.draw_bus("Level 4: Enterprise Zone", l4_bus_y, c_width)
        self.draw_bus("Level 3.5: DMZ", dmz_bus_y, c_width)
        self.draw_bus("Level 3: Operations Support (PIN)", l3_bus_y, c_width, has_switch=self.l3_has_switch)
        
        # Level 2 Buses
        self.draw_bus("Level 2: Supervisory Control (PIN)", l2_pin_y, c_width, has_switch=self.l2_has_switch)
        self.draw_bus("Level 2: Vnet/IP (Bus 1)", vnet1_y, c_width, is_dashed=True, has_switch=self.l2_has_switch)
        self.draw_bus("Level 2: Vnet/IP (Bus 2)", vnet2_y, c_width, is_dashed=True, has_switch=self.l2_has_switch)

        # --- 2. Draw Firewalls (Zones enforcement) ---
        fw_x = 60
        
        # Connect networks down the left side
        self.canvas.create_line(fw_x, l4_bus_y, fw_x, l3_bus_y, fill="#000000", width=2)
        self.canvas.create_line(fw_x, l3_bus_y, fw_x, l2_pin_y, fill="#000000", width=2)
        
        self.draw_firewall(fw_x, (l4_bus_y + dmz_bus_y) / 2, "Enterprise IT\nFW")
        self.draw_firewall(fw_x, (dmz_bus_y + l3_bus_y) / 2, "OT Boundary\nFW")
        self.draw_firewall(fw_x, (l3_bus_y + l2_pin_y) / 2, "Control PIN\nFW")

        # --- 3. Draw Level Systems (Parallel Connections) ---
        self.draw_level_systems(self.systems['l4'], l4_bus_y, c_width, connect_to=[l4_bus_y], level_key='l4', level_name="L4")
        self.draw_level_systems(self.systems['dmz'], dmz_bus_y, c_width, connect_to=[dmz_bus_y], level_key='dmz', level_name="DMZ")
        self.draw_level_systems(self.systems['l3'], l3_bus_y, c_width, connect_to=[l3_bus_y], level_key='l3', level_name="L3")
        self.draw_level_systems(self.systems['l2'], l2_pin_y, c_width, connect_to=[l2_pin_y, vnet1_y, vnet2_y], level_key='l2', level_name="L2")

        # --- 4. Draw L1 Controllers (FCS, SCS, F&G) ---
        ctrl_y = vnet2_y + 80
        
        # Dynamically position controllers based on L1 systems
        l1_instances = self._flatten_instances(self.systems['l1'])
        
        if l1_instances:
            # Draw each L1 system
            l1_system_positions = []
            num_l1 = len(l1_instances)
            spacing = (c_width - 200) / (num_l1 + 1) if num_l1 > 0 else 0
            
            for i, (l1_sys_name, level_key, equipment, inst_id) in enumerate(l1_instances):
                c_x = 150 + (spacing * (i + 1))
                
                # Lines up to Vnet 1 & 2
                self.canvas.create_line(c_x - 15, ctrl_y - 25, c_x - 15, vnet1_y, fill="#000000", width=2, dash=(4, 2))
                self.canvas.create_line(c_x + 15, ctrl_y - 25, c_x + 15, vnet2_y, fill="#000000", width=2, dash=(4, 2))
                
                # Line down to L1 Field Instruments
                self.canvas.create_line(c_x, ctrl_y + 25, c_x, ctrl_y + 90, fill="#000000", width=2)
                
                is_selected = self.selected_system and self.selected_system[1] == equipment and self.selected_system[2] == inst_id
                self.draw_node(c_x - 50, ctrl_y - 25, c_x + 50, ctrl_y + 25, l1_sys_name, 
                             is_controller=True, is_selected=is_selected,
                             level_key=level_key, equipment=equipment, inst_id=inst_id)
                l1_system_positions.append(c_x)

            # --- 5. Draw Level 1 Field Instruments (Bottom) ---
            l1_y = ctrl_y + 110
            box_left = 120
            box_right = c_width - 100
            self.draw_node(box_left, l1_y - 20, box_right, l1_y + 20, 
                          "Level 1: Field Instruments (Transmitters, Valves, Actuators, IOs)")

        # Update scroll region to fit all content
        scroll_height = max(canvas_height, ctrl_y + 150 if l1_instances else vnet2_y + 100)
        self.canvas.configure(scrollregion=(0, 0, c_width, scroll_height))

    def _flatten_instances(self, level_dict):
        """Flatten all instances in a level"""
        all_instances = []
        for equipment, instances in level_dict.items():
            for inst_id, data in instances.items():
                all_instances.append((data['name'], None, equipment, inst_id))
        return all_instances

    def draw_level_systems(self, level_dict, primary_bus_y, c_width, connect_to, level_key="", level_name=""):
        """Draw all equipment and instances for a level"""
        if not level_dict: 
            return
        
        # Flatten all instances with metadata
        all_instances = []
        for equipment, instances in level_dict.items():
            for inst_id, data in instances.items():
                all_instances.append((data['name'], level_key, equipment, inst_id))
        
        if not all_instances:
            return
        
        num_systems = len(all_instances)
        available_width = c_width - 300
        spacing = available_width / (num_systems + 1) if num_systems > 0 else 0
        y_center = primary_bus_y - 50
        
        for i, (sys_name, lk, equipment, inst_id) in enumerate(all_instances):
            x_center = 200 + (spacing * (i + 1))
            
            if len(connect_to) == 1:
                self.canvas.create_line(x_center, y_center + 25, x_center, connect_to[0], fill="#000000", width=2)
            else:
                # L2 has multiple connections
                self.canvas.create_line(x_center, y_center + 25, x_center, connect_to[0], fill="#000000", width=2)
                self.canvas.create_line(x_center - 15, y_center + 25, x_center - 15, connect_to[1], fill="#000000", width=2, dash=(4, 2))
                self.canvas.create_line(x_center + 15, y_center + 25, x_center + 15, connect_to[2], fill="#000000", width=2, dash=(4, 2))
            
            is_selected = self.selected_system and self.selected_system[1] == equipment and self.selected_system[2] == inst_id
            self.draw_node(x_center - 45, y_center - 25, x_center + 45, y_center + 25, sys_name, 
                         is_selected=is_selected, level_key=lk, equipment=equipment, inst_id=inst_id)

    def draw_bus(self, label, y, c_width, is_dashed=False, has_switch=False):
        dash_pattern = (8, 4) if is_dashed else ()
        
        # The bus line
        self.canvas.create_line(60, y, c_width - 40, y, fill="#000000", width=4, dash=dash_pattern)
        
        # Place Switch Icon on the bus if activated
        if has_switch:
            self.draw_switch_icon(170, y)
            
        # Label on the right
        self.canvas.create_text(c_width - 40, y - 15, text=label, anchor="e", font=("Segoe UI", 8, "bold"), fill="#000000")

    def draw_firewall(self, x, y, label):
        fw_w, fw_h = 32, 42
        x1, y1 = x - fw_w/2, y - fw_h/2
        x2, y2 = x + fw_w/2, y + fw_h/2
        
        self.canvas.create_rectangle(x1+2, y1+2, x2+2, y2+2, fill="#d1d5db", outline="")
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#ffffff", outline="#000000", width=2)
        
        # Hatching
        for i in range(1, 4):
            self.canvas.create_line(x1, y1 + i*10.5, x2, y1 + i*10.5, fill="#000000")
        self.canvas.create_line(x, y1, x, y1+10.5, fill="#000000")
        self.canvas.create_line(x-8, y1+10.5, x-8, y1+21, fill="#000000")
        self.canvas.create_line(x+8, y1+10.5, x+8, y1+21, fill="#000000")
        self.canvas.create_line(x, y1+21, x, y1+31.5, fill="#000000")
        self.canvas.create_line(x-8, y1+31.5, x-8, y2, fill="#000000")
        self.canvas.create_line(x+8, y1+31.5, x+8, y2, fill="#000000")
        
        self.canvas.create_text(x - 35, y, text=label, anchor="e", font=("Segoe UI", 7, "bold"), justify=tk.CENTER)

    def draw_switch_icon(self, x, y):
        sw_w, sw_h = 44, 26
        x1, y1 = x - sw_w/2, y - sw_h/2
        x2, y2 = x + sw_w/2, y + sw_h/2
        
        self.canvas.create_rectangle(x1+2, y1+2, x2+2, y2+2, fill="#d1d5db", outline="")
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#ffffff", outline="#000000", width=2)
        
        # Crossing arrows
        self.canvas.create_line(x - 12, y, x + 12, y, fill="#000000", width=1.5, arrow=tk.BOTH, arrowshape=(3, 3, 2))
        self.canvas.create_line(x, y - 5, x, y + 5, fill="#000000", width=1.5, arrow=tk.BOTH, arrowshape=(3, 3, 2))
        
        self.canvas.create_text(x, y - 22, text="Managed SW", justify=tk.CENTER, font=("Segoe UI", 7, "bold"))

    def draw_node(self, x1, y1, x2, y2, text, is_controller=False, is_selected=False, level_key="", equipment="", inst_id=None):
        # Store position for click detection
        if level_key and equipment is not None and inst_id is not None:
            sys_id = f"{level_key}_{equipment}_{inst_id}"
            self.system_positions[sys_id] = (x1, y1, x2, y2, level_key, equipment, inst_id)
        
        self.canvas.create_rectangle(x1+4, y1+4, x2+4, y2+4, fill="#e5e7eb", outline="")
        
        bw = 4 if is_selected else (3 if is_controller else 2)
        
        # Different colors for different states
        if is_selected:
            fill_color = "#FFD700"  # Gold for selected
        elif is_controller:
            fill_color = "#d4edda"  # Light green for controllers
        else:
            fill_color = "#ffffff"
        
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline="#000000", width=bw)
        
        x_c, y_c = (x1 + x2) / 2, (y1 + y2) / 2
        self.canvas.create_text(x_c, y_c, text=text, font=("Segoe UI", 8, "bold"), justify=tk.CENTER, fill="#000000", width=(x2-x1)-10)

if __name__ == "__main__":
    root = tk.Tk()
    app = YokogawaArchitectureApp(root)
    root.mainloop()
