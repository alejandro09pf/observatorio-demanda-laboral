import re
from typing import List, Dict, Any
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RegexSkill:
    """Represents a skill found by regex."""
    skill_text: str
    skill_type: str
    confidence: float
    position: tuple
    context: str
    extraction_method: str

class RegexExtractor:
    """Extract skills using regular expression patterns."""
    
    def __init__(self):
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict[str, List[str]]:
        """Load regex patterns for skill extraction."""
        return {
            'programming_languages': [
                r'\bPython\b', r'\bJavaScript\b', r'\bJava\b', r'\bC\+\+\b', r'\bC#\b',
                r'\bGo\b', r'\bRust\b', r'\bPHP\b', r'\bRuby\b', r'\bSwift\b',
                r'\bKotlin\b', r'\bTypeScript\b', r'\bScala\b', r'\bR\b', r'\bMATLAB\b',
                r'\bJulia\b', r'\bDart\b', r'\bElixir\b', r'\bClojure\b', r'\bHaskell\b'
            ],
            'frameworks_libraries': [
                r'\bReact\b', r'\bReact\.js\b', r'\bReactJS\b', r'\bAngular\b', r'\bVue\.js\b',
                r'\bVueJS\b', r'\bDjango\b', r'\bFlask\b', r'\bFastAPI\b', r'\bExpress\.js\b',
                r'\bNode\.js\b', r'\bNodeJS\b', r'\bSpring\b', r'\bLaravel\b', r'\bSymfony\b',
                r'\bASP\.NET\b', r'\bRuby on Rails\b', r'\bBootstrap\b', r'\bTailwind CSS\b',
                r'\bMaterial-UI\b', r'\bAnt Design\b', r'\bjQuery\b', r'\bRedux\b', r'\bMobX\b',
                r'\bVuex\b', r'\bNext\.js\b', r'\bNuxt\.js\b', r'\bGatsby\b'
            ],
            'databases': [
                r'\bPostgreSQL\b', r'\bMySQL\b', r'\bMongoDB\b', r'\bRedis\b', r'\bSQLite\b',
                r'\bOracle\b', r'\bSQL Server\b', r'\bMariaDB\b', r'\bCassandra\b', r'\bDynamoDB\b',
                r'\bElasticsearch\b', r'\bInfluxDB\b', r'\bNeo4j\b', r'\bCouchDB\b', r'\bArangoDB\b'
            ],
            'cloud_platforms': [
                r'\bAWS\b', r'\bAmazon Web Services\b', r'\bAzure\b', r'\bGoogle Cloud\b', r'\bGCP\b',
                r'\bDigitalOcean\b', r'\bHeroku\b', r'\bVercel\b', r'\bNetlify\b', r'\bFirebase\b',
                r'\bCloudflare\b', r'\bLinode\b', r'\bVultr\b', r'\bIBM Cloud\b', r'\bOracle Cloud\b'
            ],
            'devops_tools': [
                r'\bDocker\b', r'\bKubernetes\b', r'\bJenkins\b', r'\bGitLab CI\b', r'\bGitHub Actions\b',
                r'\bTravis CI\b', r'\bCircleCI\b', r'\bAnsible\b', r'\bTerraform\b', r'\bChef\b',
                r'\bPuppet\b', r'\bVagrant\b', r'\bPrometheus\b', r'\bGrafana\b', r'\bELK Stack\b',
                r'\bSplunk\b', r'\bDatadog\b', r'\bNew Relic\b'
            ],
            'version_control': [
                r'\bGit\b', r'\bGitHub\b', r'\bGitLab\b', r'\bBitbucket\b', r'\bSVN\b', r'\bMercurial\b'
            ],
            'data_science': [
                r'\bPandas\b', r'\bNumPy\b', r'\bMatplotlib\b', r'\bSeaborn\b', r'\bPlotly\b',
                r'\bScikit-learn\b', r'\bTensorFlow\b', r'\bPyTorch\b', r'\bKeras\b', r'\bJupyter\b',
                r'\bHadoop\b', r'\bSpark\b', r'\bKafka\b', r'\bAirflow\b', r'\bDask\b',
                r'\bXGBoost\b', r'\bLightGBM\b', r'\bCatBoost\b'
            ],
            'web_technologies': [
                r'\bHTML5\b', r'\bCSS3\b', r'\bREST\b', r'\bGraphQL\b', r'\bWebSocket\b',
                r'\bOAuth\b', r'\bJWT\b', r'\bOpenAPI\b', r'\bSwagger\b', r'\bWebpack\b',
                r'\bVite\b', r'\bParcel\b', r'\bBabel\b', r'\bESLint\b', r'\bPrettier\b',
                r'\bSass\b', r'\bLess\b', r'\bStylus\b'
            ]
        }
    
    def extract_skills(self, text: str) -> List[RegexSkill]:
        """Extract skills from text using regex patterns."""
        if not text:
            return []
        
        logger.info(f"Extracting skills with regex from text (length: {len(text)})")
        skills = []
        
        for skill_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    skill_text = match.group()
                    start, end = match.span()
                    
                    # Get context around the match
                    context_start = max(0, start - 50)
                    context_end = min(len(text), end + 50)
                    context = text[context_start:context_end].strip()
                    
                    skill = RegexSkill(
                        skill_text=skill_text,
                        skill_type=skill_type,
                        confidence=0.8,  # High confidence for exact matches
                        position=(start, end),
                        context=context,
                        extraction_method='regex'
                    )
                    skills.append(skill)
        
        # Remove duplicates
        unique_skills = self._deduplicate_skills(skills)
        logger.info(f"Found {len(unique_skills)} unique skills with regex")
        return unique_skills
    
    def _deduplicate_skills(self, skills: List[RegexSkill]) -> List[RegexSkill]:
        """Remove duplicate skills based on normalized text."""
        unique_skills = []
        seen_texts = set()
        
        for skill in skills:
            normalized = self._normalize_skill_text(skill.skill_text)
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                unique_skills.append(skill)
        
        return unique_skills
    
    def _normalize_skill_text(self, text: str) -> str:
        """Normalize skill text for comparison."""
        normalized = text.lower()
        
        # Common variations
        variations = {
            'react.js': 'react',
            'reactjs': 'react',
            'node.js': 'nodejs',
            'nodejs': 'nodejs',
            'aws': 'aws',
            'amazon web services': 'aws'
        }
        
        for variation, standard in variations.items():
            if normalized == variation:
                return standard
        
        return normalized 