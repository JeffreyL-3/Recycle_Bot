defaultObject = "object"
defaultPersonality = "a recycling expert"
defaultModel = "gpt-4o"
supportedModels = {defaultModel}

def getDefaultObject():
    return defaultObject
def getDefaultPersonality():
    return defaultPersonality
def getDefaultModel():
    return defaultModel

def getModel(model):
    return model if model in supportedModels else defaultModel
