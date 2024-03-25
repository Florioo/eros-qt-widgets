import csv
import os
import time
from typing import Dict


class CSVOutput:
    target_file_path = None
    csv_file = None
    lines_received = 0
    skip_every_n_lines = 0
    output_file = None
    start_time = None
    packets_sent = 0

    def __init__(self) -> None:
        pass

    def open(self, base_path: str, skip_every_n_lines: int = 0):
        timestamp = time.strftime("%Y%m%d-%H%M%S")

        target_file_path = os.path.join(base_path, timestamp + ".csv")

        self.output_file = open(target_file_path, "w", newline="")
        self.lines_received = 0
        self.skip_every_n_lines = skip_every_n_lines
        self.start_time = time.time()
        self.csv_file = csv.writer(self.output_file)
        self.packets_sent = 0

    def write(self, data: Dict):
        if self.csv_file is None:
            return
        data = data.copy()
        # add time
        assert self.start_time is not None
        
        data["time"] = time.time() - self.start_time

        if self.lines_received == 0:
            self.csv_file.writerow(data.keys())

        if self.lines_received % (1 + self.skip_every_n_lines) == 0:
            self.csv_file.writerow(data.values())
            self.packets_sent += 1

        self.lines_received += 1

    def close(self):
        if self.output_file is None:
            return

        self.output_file.close()
        self.output_file = None

    def is_open(self) -> bool:
        return self.output_file is not None

    def get_logged_packets(self) -> int:
        return self.packets_sent
