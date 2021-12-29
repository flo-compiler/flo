from src.errors import Error
def printError(error: Error):
    print(error.message())
    exit(1)
