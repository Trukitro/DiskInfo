import customtkinter as ctk
import win32com.client
import psutil
import os
import json
import time
from PIL import Image

# Set appearance mode and default theme
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "diskinfo_config.json"

class DiskInfoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self._init_window()
        self._init_variables()
        self._create_sidebar()
        self._create_main_frame()
        self.show_drive_info()  # Show drive info by default

    # Initialization methods
    def _init_window(self):
        self.title("💻 Drive Info Viewer")
        self.geometry("1200x800")
        self.minsize(1000, 700)

    def _init_variables(self):
        self.drive_data = {}
        self.partition_data_cache = None
        self.partition_cache_time = 0
        self.frames = {}

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar.pack_propagate(False)

        # App title
        self.logo_label = ctk.CTkLabel(
            self.sidebar, 
            text="Disk Info",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.pack(pady=20)

        # Navigation buttons
        self.nav_buttons = []
        nav_items = [
            ("🔄 Drive Info", self.show_drive_info),
            ("📊 Health Status", self.show_health),
            ("🗂️ Partitions", self.show_partitions),
            ("⚡ Benchmark", self.show_benchmark),
            ("ℹ️ About", self.show_about)  # Add new About navigation item
        ]

        for text, command in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                command=command,
                height=40,
                corner_radius=6,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                anchor="w"
            )
            btn.pack(pady=5, padx=20, fill="x")
            self.nav_buttons.append(btn)

        # Theme switcher
        self._create_theme_switcher()

    def _create_theme_switcher(self):
        self.appearance_mode_label = ctk.CTkLabel(
            self.sidebar, 
            text="Appearance Mode:",
            anchor="w"
        )
        self.appearance_mode_label.pack(padx=20, pady=(20, 0))
        
        self.appearance_mode_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode
        )
        self.appearance_mode_menu.pack(padx=20, pady=(10, 20))

    def _create_main_frame(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.pack(side="right", fill="both", expand=True)

        # Create frames for different views
        for frame_name in ["drive_info", "health", "partitions", "benchmark", "about"]:  # Add about frame
            frame = ctk.CTkScrollableFrame(
                self.main_frame,
                corner_radius=0
            )
            frame.pack(fill="both", expand=True)
            frame.pack_forget()  # Hide initially
            self.frames[frame_name] = frame

    # Add new method for About page
    def show_about(self):
        """Show about page with app information."""
        print("DEBUG: Showing about page")
        self.clear_frame("about")
        self.update_about_info()
        self.show_frame("about")
        self.highlight_nav_button(4)  # Update index for the new button

    def update_about_info(self):
        """Update about page information."""
        frame = self.frames["about"]

        # App title and version
        header = ctk.CTkLabel(
            frame,
            text="About Disk Info",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.pack(pady=20)

        version_label = ctk.CTkLabel(
            frame,
            text="Version 5.0",
            font=ctk.CTkFont(size=16)
        )
        version_label.pack(pady=(0, 20))

        # App description
        description = (
            "Disk Info is a comprehensive disk management and monitoring tool "
            "that provides detailed information about your storage devices. "
            "It helps you monitor disk health, performance, and usage."
        )
        desc_label = ctk.CTkLabel(
            frame,
            text=description,
            font=ctk.CTkFont(size=14),
            wraplength=600
        )
        desc_label.pack(pady=(0, 30))

        # Features section
        features_header = ctk.CTkLabel(
            frame,
            text="Features Guide",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        features_header.pack(pady=(0, 20))

        features = [
            ("🔄 Drive Info", "View basic information about all connected drives including capacity and usage."),
            ("📊 Health Status", "Monitor drive health using SMART data and predict potential failures."),
            ("🗂️ Partitions", "Examine detailed partition information in a Windows Disk Management style interface."),
            ("⚡ Benchmark", "Test drive read and write speeds with a built-in benchmarking tool.")
        ]

        for icon, description in features:
            feature_frame = ctk.CTkFrame(frame, corner_radius=6)
            feature_frame.pack(fill="x", padx=20, pady=10)

            feature_title = ctk.CTkLabel(
                feature_frame,
                text=icon,
                font=ctk.CTkFont(size=16, weight="bold")
            )
            feature_title.pack(padx=15, pady=(15, 5), anchor="w")

            feature_desc = ctk.CTkLabel(
                feature_frame,
                text=description,
                font=ctk.CTkFont(size=13),
                wraplength=550
            )
            feature_desc.pack(padx=15, pady=(0, 15), anchor="w")

        # Creator information
        creator_header = ctk.CTkLabel(
            frame,
            text="Creator Information",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        creator_header.pack(pady=(30, 10))

        creator_label = ctk.CTkLabel(
            frame,
            text="Created by EtchTechnologies (Rikion)",
            font=ctk.CTkFont(size=14)
        )
        creator_label.pack(pady=(0, 5))

        github_link = ctk.CTkLabel(
            frame,
            text="GitHub: https://github.com/Trukitro",
            font=ctk.CTkFont(size=14),
            text_color="blue",
            cursor="hand2"
        )
        github_link.pack(pady=(0, 20))
        github_link.bind("<Button-1>", lambda e: os.system("start https://github.com/Trukitro"))

        # Changelog section
        changelog_header = ctk.CTkLabel(
            frame,
            text="Changelog",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        changelog_header.pack(pady=(30, 10))

        changelog = [
            "Version 5.0:",
            "- Added an About page with creator information and changelog.",
            "- Improved partition information display with detailed attributes.",
            "- Enhanced benchmarking tool with better error handling.",
            "- Added support for dark mode and appearance switching.",
            "",
            "Version 4.0:",
            "- Introduced benchmarking functionality for read/write speeds.",
            "- Redesigned UI for better usability and aesthetics.",
            "- Added health monitoring using SMART data.",
            "",
            "Version 3.0:",
            "- Added partition management view similar to Windows Disk Management.",
            "- Improved drive information display with capacity and usage details.",
            "",
            "Version 2.0:",
            "- Added basic drive information display.",
            "- Introduced navigation sidebar for switching between views.",
            "",
            "Version 1.0:",
            "- Initial release with basic UI and functionality."
        ]

        for entry in changelog:
            changelog_label = ctk.CTkLabel(
                frame,
                text=entry,
                font=ctk.CTkFont(size=13),
                wraplength=600,
                anchor="w"
            )
            changelog_label.pack(pady=(0, 5), anchor="w")

    def show_frame(self, frame_name):
        for frame in self.frames.values():
            frame.pack_forget()
        self.frames[frame_name].pack(fill="both", expand=True)

    def clear_frame(self, frame_name):
        for widget in self.frames[frame_name].winfo_children():
            widget.destroy()

    def highlight_nav_button(self, index):
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")

    # UI Page methods
    def show_drive_info(self):
        print("DEBUG: Showing drive info page")
        self.clear_frame("drive_info")
        self.update_drive_info()
        self.show_frame("drive_info")
        self.highlight_nav_button(0)

    def show_health(self):
        print("DEBUG: Showing health status page")
        self.clear_frame("health")
        self.update_health_info()
        self.show_frame("health")
        self.highlight_nav_button(1)

    def show_partitions(self):
        print("DEBUG: Showing partitions page")
        self.clear_frame("partitions")
        
        current_time = time.time()
        if self.partition_data_cache and current_time - self.partition_cache_time < 30:
            print("DEBUG: Using cached partition data")
            self.update_partition_info(use_cache=True)
        else:
            print("DEBUG: Fetching fresh partition data")
            self.update_partition_info(use_cache=False)
                
        self.show_frame("partitions")
        self.highlight_nav_button(2)

    def show_benchmark(self):
        print("DEBUG: Showing benchmark page")
        self.clear_frame("benchmark")
        self.update_benchmark_info()
        self.show_frame("benchmark")
        self.highlight_nav_button(3)

    # Helper methods
    def bytes_to_gb(self, bytes_val):
        return round(bytes_val / (1024 ** 3), 2)

    def change_appearance_mode(self, new_appearance_mode):
        ctk.set_appearance_mode(new_appearance_mode)

    def create_info_card(self, parent, title, content, progress_value=None):
        card = ctk.CTkFrame(parent, corner_radius=6)
        card.pack(fill="x", padx=20, pady=10)

        title_label = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(padx=15, pady=(15, 5), anchor="w")

        content_label = ctk.CTkLabel(
            card,
            text=content,
            font=ctk.CTkFont(size=13)
        )
        content_label.pack(padx=15, pady=(0, 15), anchor="w")

        if progress_value is not None:
            progress = ctk.CTkProgressBar(card, height=10)
            progress.pack(padx=15, pady=(0, 15), fill="x")
            progress.set(progress_value / 100)

    def get_drive_mappings(self):
        """Get drive mappings and information."""
        print("DEBUG: Starting get_drive_mappings")
        drive_data = {}
        try:
            print("DEBUG: Getting basic disk information using psutil")
            for partition in psutil.disk_partitions():
                try:
                    print(f"DEBUG: Processing partition {partition.mountpoint}")
                    usage = psutil.disk_usage(partition.mountpoint)
                    drive_letter = partition.mountpoint.rstrip('\\')
                    
                    if drive_letter not in drive_data:
                        print(f"DEBUG: Adding new drive {drive_letter}")
                        drive_data[drive_letter] = {
                            "model": partition.device,
                            "interface": "Storage Device",
                            "size": usage.total,
                            "partitions": []
                        }
                    
                    print(f"DEBUG: Adding partition info for {partition.mountpoint}")
                    drive_data[drive_letter]["partitions"].append({
                        "mountpoint": partition.mountpoint,
                        "used": usage.used,
                        "total": usage.total,
                        "percent": usage.percent
                    })
                except (PermissionError, FileNotFoundError) as e:
                    print(f"DEBUG: Error processing partition {partition.mountpoint}: {e}")
                    continue

            print("DEBUG: Scheduling WMI update")
            self.after(100, self.update_drive_details, drive_data)
            return drive_data

        except Exception as e:
            print(f"DEBUG: Error in get_drive_mappings: {e}")
            return {}

    def run_benchmark(self, drive, frame):
        """Run benchmark for selected drive and update results."""
        print(f"DEBUG: Running benchmark for drive {drive}")
        
        # Find and clear previous results
        for widget in frame.winfo_children():
            if hasattr(widget, '_name') and widget._name == "benchmark_results":
                for child in widget.winfo_children():
                    child.destroy()
                results_frame = widget
                break
        
        # Add loading indicator
        loading_label = ctk.CTkLabel(
            results_frame,
            text="Running benchmark...",
            font=ctk.CTkFont(size=14)
        )
        loading_label.pack(pady=10)
        
        # Update UI to show progress
        self.update()
        
        # Run benchmark
        write_speed, read_speed = self.benchmark_drive(drive)
        
        # Remove loading indicator
        loading_label.destroy()
        
        if write_speed is not None and read_speed is not None:
            # Format speeds to show GB/s if speed exceeds 1000 MB/s
            def format_speed(speed):
                if speed >= 1000:
                    return f"{speed/1000:.2f} GB/s"
                return f"{speed:.2f} MB/s"
            
            write_speed_text = format_speed(write_speed)
            read_speed_text = format_speed(read_speed)
            
            results_text = (
                f"Write Speed: {write_speed_text}\n"
                f"Read Speed: {read_speed_text}"
            )
            result_label = ctk.CTkLabel(
                results_frame,
                text=results_text,
                font=ctk.CTkFont(size=14)
            )
            result_label.pack(pady=10)
        else:
            error_label = ctk.CTkLabel(
                results_frame,
                text="Benchmark failed. Please check drive permissions.",
                text_color="red",
                font=ctk.CTkFont(size=14)
            )
            error_label.pack(pady=10)
            
    def update_benchmark_info(self):
        """Update benchmark information display."""
        frame = self.frames["benchmark"]
        
        header = ctk.CTkLabel(
            frame,
            text="Disk Benchmark",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.pack(pady=20)
        
        # Add benchmark UI here
        info_label = ctk.CTkLabel(
            frame,
            text="Select a drive to benchmark read/write speeds:",
            font=ctk.CTkFont(size=14)
        )
        info_label.pack(pady=(0, 20))
        
        # Get available drives
        drives = []
        for drive_letter in self.drive_data.keys():
            drives.append(drive_letter)
        
        if not drives:
            no_drives_label = ctk.CTkLabel(
                frame,
                text="No drives available for benchmarking",
                text_color="red"
            )
            no_drives_label.pack(pady=20)
            return
        
        # Drive selection
        drive_var = ctk.StringVar(value=drives[0])
        drive_menu = ctk.CTkOptionMenu(
            frame,
            values=drives,
            variable=drive_var
        )
        drive_menu.pack(pady=(0, 20))
        
        # Benchmark button
        benchmark_button = ctk.CTkButton(
            frame,
            text="Run Benchmark",
            command=lambda: self.run_benchmark(drive_var.get(), frame)
        )
        benchmark_button.pack(pady=(0, 20))
        
        # Results area
        results_frame = ctk.CTkFrame(frame)
        results_frame.pack(fill="x", padx=20, pady=10)
        
        # Add a tag to identify this frame
        results_frame._name = "benchmark_results"
        
        results_label = ctk.CTkLabel(
            results_frame,
            text="Benchmark Results",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        results_label.pack(pady=10)
        
        info_text = ctk.CTkLabel(
            results_frame,
            text="Click 'Run Benchmark' to test drive performance",
            font=ctk.CTkFont(size=12)
        )
        info_text.pack(pady=(0, 10))

    # Data retrieval methods
    def update_drive_info(self):
        self.drive_data = self.get_drive_mappings()
        frame = self.frames["drive_info"]
        
        header = ctk.CTkLabel(
            frame,
            text="Drive Information",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.pack(pady=20)

        for info in self.drive_data.values():
            drive_title = f"📀 {info['model']}"
            drive_content = f"Interface: {info['interface']}\nCapacity: {self.bytes_to_gb(info['size'])} GB"
            self.create_info_card(frame, drive_title, drive_content)

            for part in info["partitions"]:
                part_title = f"💾 {part['mountpoint']}"
                part_content = f"Used: {self.bytes_to_gb(part['used'])} GB of {self.bytes_to_gb(part['total'])} GB"
                self.create_info_card(frame, part_title, part_content, part['percent'])

    def get_drive_health(self):
        """Get drive health information using WMI."""
        print("DEBUG: Starting get_drive_health")
        health_data = {}
        try:
            print("DEBUG: Connecting to WMI for health info")
            wmi = win32com.client.Dispatch("WbemScripting.SWbemLocator")
            service = wmi.ConnectServer(".", "root\\cimv2")
            
            print("DEBUG: Querying disk drives for health")
            for disk in service.ExecQuery("SELECT * FROM Win32_DiskDrive"):
                print(f"DEBUG: Processing health for disk {disk.DeviceID}")
                health_data[disk.DeviceID] = {
                    "model": disk.Model,
                    "status": disk.Status if hasattr(disk, "Status") else "OK",
                    "predicted_failure": False,
                    "reason": "No issues detected",
                    "health_percentage": 100
                }
                
                try:
                    print("DEBUG: Attempting to get SMART status")
                    smart_service = wmi.ConnectServer(".", "root\\wmi")
                    for smart in smart_service.ExecQuery("SELECT * FROM MSStorageDriver_FailurePredictStatus"):
                        if disk.DeviceID in smart.InstanceName:
                            print(f"DEBUG: Found SMART data for {disk.DeviceID}")
                            health_data[disk.DeviceID].update({
                                "predicted_failure": smart.PredictFailure,
                                "reason": smart.Reason if hasattr(smart, "Reason") else "Unknown",
                                "health_percentage": 50 if smart.PredictFailure else 100
                            })
                except Exception as e:
                    print(f"DEBUG: Error getting SMART status: {e}")

        except Exception as e:
            print(f"DEBUG: Error in get_drive_health: {e}")
            
        return health_data

    def benchmark_drive(self, mountpoint):
        """Run read/write benchmark on specified drive."""
        print(f"DEBUG: Starting benchmark for {mountpoint}")
        try:
            test_file = os.path.join(mountpoint, "benchmark_test_file")
            data = b"0" * (1024 * 1024 * 10)  # 10 MB of data

            print("DEBUG: Starting write speed test")
            start_time = time.time()
            with open(test_file, "wb") as f:
                f.write(data)
            write_time = time.time() - start_time
            write_speed = 10 / write_time
            print(f"DEBUG: Write speed: {write_speed:.2f} MB/s")

            print("DEBUG: Starting read speed test")
            start_time = time.time()
            with open(test_file, "rb") as f:
                f.read()
            read_time = time.time() - start_time
            read_speed = 10 / read_time
            print(f"DEBUG: Read speed: {read_speed:.2f} MB/s")

            print("DEBUG: Cleaning up test file")
            os.remove(test_file)
            return write_speed, read_speed

        except Exception as e:
            print(f"DEBUG: Benchmark error: {e}")
            return None, None

    # UI update methods
    def update_drive_info(self):
        self.drive_data = self.get_drive_mappings()
        frame = self.frames["drive_info"]
        
        header = ctk.CTkLabel(
            frame,
            text="Drive Information",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.pack(pady=20)

        for info in self.drive_data.values():
            drive_title = f"📀 {info['model']}"
            drive_content = f"Interface: {info['interface']}\nCapacity: {self.bytes_to_gb(info['size'])} GB"
            self.create_info_card(frame, drive_title, drive_content)

            for part in info["partitions"]:
                part_title = f"💾 {part['mountpoint']}"
                part_content = f"Used: {self.bytes_to_gb(part['used'])} GB of {self.bytes_to_gb(part['total'])} GB"
                self.create_info_card(frame, part_title, part_content, part['percent'])

    def update_health_info(self):
        """Update health information display."""
        frame = self.frames["health"]
        health_data = self.get_drive_health()
        
        header = ctk.CTkLabel(
            frame,
            text="Drive Health Status",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.pack(pady=20)

        for drive_id, health in health_data.items():
            title = f"💿 Drive {drive_id}"
            content = f"Health Status: {'Healthy' if not health['predicted_failure'] else 'Warning'}\n"
            content += f"Reason: {health['reason']}"
            self.create_info_card(frame, title, content, health['health_percentage'])

    def update_partition_info(self, use_cache=False):
        """Update partition information display to emulate Windows Disk Management."""
        frame = self.frames["partitions"]
        
        # Clear existing content
        for widget in frame.winfo_children():
            widget.destroy()
        
        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        header = ctk.CTkLabel(
            header_frame,
            text="Disk Management",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.pack(side="left", pady=5)
        
        # Add refresh button
        refresh_button = ctk.CTkButton(
            header_frame,
            text="🔄 Refresh",
            command=lambda: self.show_partitions(),
            width=100
        )

        refresh_button.pack(side="right", padx=20)

        # Add loading indicator
        loading_label = ctk.CTkLabel(
            frame,
            text="Loading partition information...",
            font=ctk.CTkFont(size=14)
        )
        loading_label.pack(pady=20)

        # Use after method to allow UI to update before heavy processing
        self.after(100, lambda: self._load_partition_data(frame, loading_label))

    def _load_partition_data(self, frame, loading_label):
        """Load partition data in background thread."""
        try:
            wmi = win32com.client.Dispatch("WbemScripting.SWbemLocator")
            service = wmi.ConnectServer(".", "root\\cimv2")

            # Remove loading indicator when done
            loading_label.destroy()
            
            # Get physical disk information first
            for disk in service.ExecQuery("SELECT * FROM Win32_DiskDrive"):
                # Create a container for this disk
                disk_container = ctk.CTkFrame(frame, corner_radius=0, fg_color="transparent")
                disk_container.pack(fill="x", padx=20, pady=(0, 30), anchor="n")
                
                # Disk header with model and size
                disk_id = disk.DeviceID.split('\\')[-1]
                total_size_gb = round(int(disk.Size) / (1024**3), 2)
                
                disk_header_frame = ctk.CTkFrame(disk_container, corner_radius=0, fg_color=("gray90", "gray20"))
                disk_header_frame.pack(fill="x", pady=(0, 1))
                
                disk_header = ctk.CTkLabel(
                    disk_header_frame,
                    text=f"{disk_id} {disk.Model}",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    anchor="w"
                )
                disk_header.pack(side="left", padx=10, pady=5)
                
                disk_size = ctk.CTkLabel(
                    disk_header_frame,
                    text=f"Total size: {total_size_gb} GB",
                    font=ctk.CTkFont(size=12),
                    anchor="e"
                )
                disk_size.pack(side="right", padx=10, pady=5)
                
                # Create disk info section (similar to Windows Disk Management)
                disk_info_frame = ctk.CTkFrame(disk_container, corner_radius=0, height=120, fg_color=("gray95", "gray15"))
                disk_info_frame.pack(fill="x")
                disk_info_frame.pack_propagate(False)
                
                # Left side - Basic disk info
                basic_info_frame = ctk.CTkFrame(disk_info_frame, corner_radius=0, width=200, fg_color="transparent")
                basic_info_frame.pack(side="left", fill="y", padx=10, pady=10)
                
                # Disk number
                disk_num_label = ctk.CTkLabel(
                    basic_info_frame,
                    text=f"Disk {disk_id.replace('PHYSICALDRIVE', '')}",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    anchor="w"
                )
                disk_num_label.pack(anchor="w", pady=(5, 2))
                
                # Basic disk status
                status_label = ctk.CTkLabel(
                    basic_info_frame,
                    text="Basic",
                    font=ctk.CTkFont(size=12),
                    anchor="w"
                )
                status_label.pack(anchor="w", pady=2)
                
                # Online status
                online_label = ctk.CTkLabel(
                    basic_info_frame,
                    text="Online",
                    font=ctk.CTkFont(size=12),
                    anchor="w"
                )
                online_label.pack(anchor="w", pady=2)
                
                # Capacity
                capacity_label = ctk.CTkLabel(
                    basic_info_frame,
                    text=f"{total_size_gb} GB",
                    font=ctk.CTkFont(size=12),
                    anchor="w"
                )
                capacity_label.pack(anchor="w", pady=2)
                
                # Unallocated space
                unallocated_label = ctk.CTkLabel(
                    basic_info_frame,
                    text="Calculating...",
                    font=ctk.CTkFont(size=12),
                    anchor="w"
                )
                unallocated_label.pack(anchor="w", pady=2)
                
                # Right side - Partition layout
                partition_layout = ctk.CTkFrame(disk_info_frame, corner_radius=0, fg_color="transparent")
                partition_layout.pack(side="right", fill="both", expand=True, padx=10, pady=10)
                
                # Get all partitions for this disk
                partitions = []
                unallocated_start = 0
                for partition in service.ExecQuery(f"ASSOCIATORS OF {{Win32_DiskDrive.DeviceID='{disk.DeviceID}'}} WHERE AssocClass = Win32_DiskDriveToDiskPartition"):
                    for logical_disk in service.ExecQuery(f"ASSOCIATORS OF {{Win32_DiskPartition.DeviceID='{partition.DeviceID}'}} WHERE AssocClass = Win32_LogicalDiskToPartition"):
                        try:
                            usage = psutil.disk_usage(logical_disk.DeviceID)
                            start_offset = int(partition.StartingOffset) if hasattr(partition, 'StartingOffset') else unallocated_start
                            
                            # Check for unallocated space before this partition
                            if start_offset > unallocated_start:
                                unallocated_size = start_offset - unallocated_start
                                partitions.append({
                                    'start': unallocated_start,
                                    'size': unallocated_size,
                                    'is_unallocated': True
                                })
                            
                            partitions.append({
                                'start': start_offset,
                                'size': usage.total,
                                'used': usage.used,
                                'letter': logical_disk.DeviceID,
                                'filesystem': logical_disk.FileSystem,
                                'type': partition.Type,
                                'bootable': partition.Bootable,
                                'primary': partition.PrimaryPartition,
                                'is_unallocated': False
                            })
                            unallocated_start = start_offset + usage.total
                        except (PermissionError, FileNotFoundError):
                            continue

                # Add final unallocated space if any
                if unallocated_start < int(disk.Size):
                    partitions.append({
                        'start': unallocated_start,
                        'size': int(disk.Size) - unallocated_start,
                        'is_unallocated': True
                    })

                # Sort partitions by start position
                partitions.sort(key=lambda x: x['start'])
                
                # Calculate total unallocated space
                unallocated_space = sum(part['size'] for part in partitions if part.get('is_unallocated', False))
                unallocated_label.configure(text=f"Unallocated: {self.bytes_to_gb(unallocated_space)} GB")

                # Create visual representation of partitions
                partition_bar = ctk.CTkFrame(partition_layout, corner_radius=0, height=60, fg_color="transparent")
                partition_bar.pack(fill="x")
                
                # Calculate total width
                total_width = partition_layout.winfo_width() if partition_layout.winfo_width() > 1 else 800
                
                # Create partition blocks
                for part in partitions:
                    part_width = max(int((part['size'] / int(disk.Size)) * total_width), 50)
                    
                    if part.get('is_unallocated', False):
                        # Unallocated space - black hatched pattern
                        part_frame = ctk.CTkFrame(
                            partition_bar, 
                            width=part_width, 
                            height=60, 
                            corner_radius=0,
                            fg_color=("gray80", "gray30"),
                            border_width=1,
                            border_color=("gray60", "gray40")
                        )
                        part_frame.pack(side="left", padx=1)
                        part_frame.pack_propagate(False)
                        
                        label = ctk.CTkLabel(
                            part_frame,
                            text=f"Unallocated\n{self.bytes_to_gb(part['size'])} GB",
                            font=ctk.CTkFont(size=11),
                            text_color=("gray20", "gray90")
                        )
                        label.pack(expand=True)
                    else:
                        # Regular partition - blue for primary
                        part_frame = ctk.CTkFrame(
                            partition_bar, 
                            width=part_width, 
                            height=60, 
                            corner_radius=0,
                            fg_color=("#3498db", "#2980b9"),
                            border_width=1,
                            border_color=("gray60", "gray40")
                        )
                        part_frame.pack(side="left", padx=1)
                        part_frame.pack_propagate(False)

                        # Partition label with drive letter and size
                        label = ctk.CTkLabel(
                            part_frame,
                            text=f"{part['letter']}\n{self.bytes_to_gb(part['size'])} GB\n{part['filesystem']}",
                            font=ctk.CTkFont(size=11, weight="bold"),
                            text_color=("white", "white")
                        )
                        label.pack(expand=True)
                
                # Create partition details table
                details_frame = ctk.CTkFrame(disk_container, corner_radius=0, fg_color=("white", "gray10"))
                details_frame.pack(fill="x")
                
                # Table headers
                headers = ["Partition", "Type", "File System", "Status", "Capacity", "% Used"]
                header_frame = ctk.CTkFrame(details_frame, corner_radius=0, fg_color=("gray90", "gray20"))
                header_frame.pack(fill="x")
                
                for i, header in enumerate(headers):
                    header_label = ctk.CTkLabel(
                        header_frame,
                        text=header,
                        font=ctk.CTkFont(size=12, weight="bold"),
                        width=120 if i > 0 else 150
                    )
                    header_label.pack(side="left", padx=5, pady=5)
                
                # Table rows for each partition
                for part in partitions:
                    if not part.get('is_unallocated', False):
                        row_frame = ctk.CTkFrame(details_frame, corner_radius=0, fg_color="transparent")
                        row_frame.pack(fill="x", pady=1)
                        
                        # Partition letter
                        part_label = ctk.CTkLabel(
                            row_frame,
                            text=part['letter'],
                            font=ctk.CTkFont(size=12),
                            width=150
                        )
                        part_label.pack(side="left", padx=5, pady=5)
                        
                        # Type
                        type_label = ctk.CTkLabel(
                            row_frame,
                            text="Primary" if part.get('primary', True) else "Logical",
                            font=ctk.CTkFont(size=12),
                            width=120
                        )
                        type_label.pack(side="left", padx=5, pady=5)
                        
                        # File System
                        fs_label = ctk.CTkLabel(
                            row_frame,
                            text=part.get('filesystem', 'Unknown'),
                            font=ctk.CTkFont(size=12),
                            width=120
                        )
                        fs_label.pack(side="left", padx=5, pady=5)
                        
                        # Status
                        status_label = ctk.CTkLabel(
                            row_frame,
                            text="Healthy",
                            font=ctk.CTkFont(size=12),
                            width=120
                        )
                        status_label.pack(side="left", padx=5, pady=5)
                        
                        # Capacity
                        capacity_label = ctk.CTkLabel(
                            row_frame,
                            text=f"{self.bytes_to_gb(part['size'])} GB",
                            font=ctk.CTkFont(size=12),
                            width=120
                        )
                        capacity_label.pack(side="left", padx=5, pady=5)
                        
                        # % Used
                        percent_used = round((part['used'] / part['size']) * 100, 1) if 'used' in part else 0
                        percent_label = ctk.CTkLabel(
                            row_frame,
                            text=f"{percent_used}%",
                            font=ctk.CTkFont(size=12),
                            width=120
                        )
                        percent_label.pack(side="left", padx=5, pady=5)

        except Exception as e:
            print(f"Error updating partition info: {e}")
            error_label = ctk.CTkLabel(
                frame,
                text=f"Error loading partition information: {str(e)}",
                text_color="red"
            )
            error_label.pack(pady=20)

    def update_drive_details(self, drive_data):
        """Update drive details with WMI information in background."""
        print("DEBUG: Starting update_drive_details")
        try:
            print("DEBUG: Connecting to WMI")
            # In your _load_partition_data method, wrap the WMI queries in try-except blocks:
            try:
                wmi = win32com.client.Dispatch("WbemScripting.SWbemLocator")
                service = wmi.ConnectServer(".", "root\\cimv2")
                
                print("DEBUG: Querying disk drives")
                for disk in service.ExecQuery("SELECT * FROM Win32_DiskDrive"):
                    print(f"DEBUG: Processing disk {disk.DeviceID}")
                    for partition in service.ExecQuery(f"ASSOCIATORS OF {{Win32_DiskDrive.DeviceID='{disk.DeviceID}'}} WHERE AssocClass = Win32_DiskDriveToDiskPartition"):
                        print(f"DEBUG: Found partition {partition.DeviceID}")
                        for logical_disk in service.ExecQuery(f"ASSOCIATORS OF {{Win32_DiskPartition.DeviceID='{partition.DeviceID}'}} WHERE AssocClass = Win32_LogicalDiskToPartition"):
                            drive_letter = logical_disk.DeviceID.rstrip('\\')
                            print(f"DEBUG: Updating info for drive {drive_letter}")
                            if drive_letter in drive_data:
                                drive_data[drive_letter]["model"] = disk.Model
                                drive_data[drive_letter]["interface"] = disk.InterfaceType
                    
                print("DEBUG: Updating display with new information")
                self.drive_data = drive_data
                # Instead of calling update_drive_info which would start the cycle again,
                # we'll update the display directly
                frame = self.frames["drive_info"]
                self.clear_frame("drive_info")
                
                header = ctk.CTkLabel(
                    frame,
                    text="Drive Information",
                    font=ctk.CTkFont(size=24, weight="bold")
                )
                header.pack(pady=20)

                for info in self.drive_data.values():
                    drive_title = f"📀 {info['model']}"
                    drive_content = f"Interface: {info['interface']}\nCapacity: {self.bytes_to_gb(info['size'])} GB"
                    self.create_info_card(frame, drive_title, drive_content)

                    for part in info["partitions"]:
                        part_title = f"💾 {part['mountpoint']}"
                        part_content = f"Used: {self.bytes_to_gb(part['used'])} GB of {self.bytes_to_gb(part['total'])} GB"
                        self.create_info_card(frame, part_title, part_content, part['percent'])    

            except Exception as e:
                print(f"DEBUG: Error in update_drive_details: {e}")
                
        except Exception as e:
                print(f"DEBUG: Error in update_drive_details: {e}")

if __name__ == "__main__":
    app = DiskInfoApp()
    app.mainloop()