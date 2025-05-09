# DiskInfo

DiskInfo is a comprehensive disk management and monitoring tool that provides detailed information about your storage devices. It helps you monitor disk health, performance, and usage, and includes features like benchmarking and partition management.

---

## Features

- **Drive Info**: View basic information about all connected drives, including capacity and usage.
- **Health Status**: Monitor drive health using SMART data and predict potential failures.
- **Partitions**: Examine detailed partition information in a Windows Disk Management-style interface.
- **Benchmark**: Test drive read and write speeds with a built-in benchmarking tool.
- **Dark Mode**: Switch between light and dark themes for better usability.

---

## Installation

### Prerequisites
- Python 3.10 or higher
- Required Python libraries:
  - `customtkinter`
  - `psutil`
  - `win32com.client`
  - `Pillow`

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/Trukitro/DiskInfo.git
   cd DiskInfo