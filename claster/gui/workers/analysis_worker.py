"""
Background worker for long-running analysis tasks with progress reporting.
"""

from PyQt6.QtCore import QThread, pyqtSignal


class AnalysisWorker(QThread):
    progress = pyqtSignal(int, int)
    message = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            if 'callback' in self.func.__code__.co_varnames:
                self.kwargs['callback'] = self.progress.emit
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))