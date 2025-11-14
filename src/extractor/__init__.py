# Lazy imports to avoid circular dependencies and optional dependencies
# Import only what's needed to avoid loading heavy modules like faiss

__all__ = ['ExtractionPipeline', 'NERExtractor', 'RegexExtractor', 'ESCOMatcher']

# These will be imported on-demand when accessed
def __getattr__(name):
    if name == 'ExtractionPipeline':
        from .pipeline import ExtractionPipeline
        return ExtractionPipeline
    elif name == 'NERExtractor':
        from .ner_extractor import NERExtractor
        return NERExtractor
    elif name == 'RegexExtractor':
        from .regex_patterns import RegexExtractor
        return RegexExtractor
    elif name == 'ESCOMatcher':
        from .esco_matcher import ESCOMatcher
        return ESCOMatcher
    raise AttributeError(f"module {__name__} has no attribute {name}")
