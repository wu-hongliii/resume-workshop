from multiprocessing import freeze_support

from app.main import run


if __name__ == "__main__":
    freeze_support()
    run()
