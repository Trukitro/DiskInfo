# DiskInfo

DiskInfo is a comprehensive disk management and monitoring tool that provides detailed information about your storage devices. It helps you monitor disk health, performance, and usage, and includes features like benchmarking and partition management.

---

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Screenshots](#screenshots)
- [Changelog](#changelog)
- [Creator](#creator)
- [Contributing](#contributing)
- [License](#license)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)
- [Roadmap](#roadmap)
- [Acknowledgments](#acknowledgments)

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
   ```

---

## Troubleshooting

### Common Issues

1. **Missing Dependencies**:
   - If you encounter an error about missing libraries, ensure you have installed all required dependencies:
     ```bash
     pip install -r requirements.txt
     ```

2. **Permission Denied Errors**:
   - Run the application as an administrator if you encounter permission issues accessing certain drives.

3. **SMART Data Not Available**:
   - Some drives may not support SMART data. Check your drive's specifications.

4. **Benchmark Errors**:
   - Ensure the drive is writable and has sufficient free space for the benchmark test.

If you encounter other issues, feel free to open an issue on the [GitHub repository](https://github.com/Trukitro/DiskInfo/issues).

---

## Advanced Usage

### Debug Mode
Run the application in debug mode to see detailed logs:
```bash
python DiskInfov5.py --debug
```

---

## Roadmap

Here are some planned features and improvements for future releases:

- Add support for monitoring network drives.
- Export drive and partition information to CSV or JSON files.
- Provide detailed SMART data reports for advanced users.
- Add a notification system for drive health warnings.
- Include multi-language support for international users.

Feel free to suggest additional features by opening an issue on the [GitHub repository](https://github.com/Trukitro/DiskInfo/issues).

---

## Acknowledgments

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for the modern UI framework.
- [Psutil](https://github.com/giampaolo/psutil) for system and disk information.
- [Pillow](https://python-pillow.org/) for image handling.
- The Python community for their support and contributions.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.