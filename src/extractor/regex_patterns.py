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
        # EXPERIMENT #9.1: Stopwords for bullet_point_skills to fix Precision 20.57%
        self.BULLET_STOPWORDS = {
            # Prepositions (from "easy-to-use", "end-to-end")
            'to', 'in', 'of', 'as', 'by', 'on', 'at', 'or', 'an', 'is', 'it', 'end',
            # Single letters (from "S.A. de C.V.")
            'c', 'r', 'd', 'e', 's', 'a', 'b', 'p', 'm', 'n', 'o', 'q', 'u', 'v', 'w', 'x', 'y', 'z',
            # HTML/JS garbage (from "window.ctLytics Piano")
            'piano', 'cat', 'true', 'false', 'type', 'search', 'window',
            'data', 'var', 'const', 'let', 'function', 'document'
        }
    
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
                # CRITICAL: Multi-word patterns BEFORE single-word to avoid partial matches
                # Example: "Spring Boot" must match before "Spring" alone
                r'\bSpring\s+Boot\b', r'\bRuby on Rails\b', r'\bTailwind\s+CSS\b',
                r'\bMaterial[-\s]UI\b', r'\bAnt\s+Design\b', r'\bStyled\s+Components\b',
                r'\bExpress\.?js\b', r'\bNode\.?js\b', r'\bReact\.?js\b', r'\bVue\.?js\b',
                r'\bNext\.?js\b', r'\bNuxt\.?js\b',
                # Single-word patterns
                r'\bReact\b', r'\bReactJS\b', r'\bAngular\b', r'\bVueJS\b', r'\bDjango\b',
                r'\bFlask\b', r'\bFastAPI\b', r'\bNodeJS\b', r'\bSpring\b', r'\bLaravel\b',
                r'\bSymfony\b', r'\bASP\.NET\b', r'\bBootstrap\b', r'\bjQuery\b', r'\bRedux\b',
                r'\bMobX\b', r'\bVuex\b', r'\bGatsby\b'
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
            ],
            # ===================================================================
            # DOMAIN-SPECIFIC PATTERNS (FASE 3 - Mejora #7)
            # ===================================================================
            # .NET Ecosystem (commonly missing in Exp #6)
            'dotnet_ecosystem': [
                r'\b\.NET\s+Core\b', r'\b\.NET\s+5\b', r'\b\.NET\s+6\b', r'\b\.NET\s+7\b', r'\b\.NET\s+8\b',
                r'\bASP\.NET\s+Core\b', r'\bASP\.NET\s+Core\s+MVC\b', r'\bASP\.NET\s+Web\s+API\b',
                r'\bEntity\s+Framework\s+Core\b', r'\bEntity\s+Framework\b',
                r'\b\.NET\s+MAUI\b', r'\bBlazor\b', r'\bSignalR\b', r'\bMinimal\s+APIs\b',
                r'\bC#\b', r'\bF#\b', r'\bVB\.NET\b',
            ],
            # Build & Test Tools (commonly missing)
            'build_test_tools': [
                r'\bMaven\b', r'\bGradle\b', r'\bAnt\b', r'\bMSBuild\b', r'\bNuGet\b',
                r'\bJUnit\b', r'\bJUnit\s+5\b', r'\bTestNG\b', r'\bMockito\b',
                r'\bPytest\b', r'\bPHPUnit\b', r'\bJest\b', r'\bMocha\b', r'\bChai\b',
                r'\bSelenium\b', r'\bCypress\b', r'\bPlaywright\b', r'\bPuppeteer\b',
                r'\bSonarQube\b', r'\bSonarLint\b', r'\bJaCoCo\b',
            ],
            # Cloud Services (specific services commonly missing)
            'cloud_services': [
                r'\bAWS\s+Lambda\b', r'\bAWS\s+EC2\b', r'\bAWS\s+S3\b', r'\bAWS\s+RDS\b',
                r'\bAzure\s+Functions\b', r'\bAzure\s+App\s+Service\b', r'\bAzure\s+DevOps\b',
                r'\bEvent\s+Grid\b', r'\bService\s+Bus\b', r'\bLogic\s+Apps\b',
                r'\bGoogle\s+Cloud\s+Functions\b', r'\bGoogle\s+Cloud\s+Run\b',
                r'\bCosmos\s+DB\b', r'\bDynamoDB\b', r'\bFirestore\b',
            ],
            # Compound Skills (CI/CD, REST API, etc.)
            'compound_skills': [
                r'\bCI/CD\b', r'\bCI\s*/\s*CD\b',
                r'\bREST\s+API\b', r'\bREST\s+APIs\b', r'\bRESTful\s+API\b',
                r'\bGraphQL\s+API\b',
                r'\bEvent-Driven\s+Architecture\b', r'\bEvent\s+Driven\b',
                r'\bService-Oriented\s+Architecture\b', r'\bSOA\b',
                r'\bObject-Oriented\s+Programming\b', r'\bOOP\b',
                r'\bProgramación\s+orientada\s+a\s+objetos\b', r'\bPOO\b',
                r'\bTest-Driven\s+Development\b', r'\bTDD\b',
                r'\bBehavior-Driven\s+Development\b', r'\bBDD\b',
                r'\bDomain-Driven\s+Design\b', r'\bDDD\b',
            ],
            # Business Intelligence & Data
            'bi_data_tools': [
                r'\bPower\s+BI\b', r'\bPower\s+BI\s+Desktop\b', r'\bPower\s+BI\s+Service\b',
                r'\bTableau\b', r'\bQlik\b', r'\bLooker\b', r'\bMetabase\b',
                r'\bDatabricks\b', r'\bSnowflake\b', r'\bRedshift\b',
                r'\bData\s+Lake\b', r'\bData\s+Warehouse\b', r'\bData\s+Pipeline\b',
                r'\bDAX\b', r'\bPower\s+Query\b', r'\bM\s+language\b',
                # SQL-specific (from NER analysis)
                r'\bCTE\b', r'\bOLS\b', r'\bRLS\b', r'\bParquet\b', r'\bDelta\b',
            ],
            # ===================================================================
            # NER-UNIQUE SKILLS (Experimento #8 - 2025-01-05)
            # ===================================================================
            # Skills que SOLO NER encontraba (27 total) ahora en Regex para evitar dependencia
            # Fuente: analyze_ner_performance.py - 41.9% precision pero 27 skills únicas valiosas
            'ner_migrated_skills': [
                # Cloud/Services
                r'\bAPI\s+Gateway\b', r'\bIAM\b', r'\bWeb\s+Services\b',
                # APIs & Data formats
                r'\bSOAP\b', r'\bSOAPUI\b', r'\bJSON\b', r'\bSSR\b',
                # Frontend tools
                r'\bSCSS\b', r'\bSEO\b', r'\bCSRF\b',
                # Third-party services
                r'\bAbly\b', r'\bMapbox\b', r'\bTwilio\b', r'\bStripe\b', r'\bSentry\b',
                # Frameworks & libraries (que faltaban)
                r'\bQuarkus\b', r'\bLogback\b',
                # Methodology
                r'\bScrum\b',
                # Tools (ya teníamos Excel pero lo reforzamos)
                r'\bExcel\b',
            ],
            # ===================================================================
            # MISSING EXACT SKILLS (Experimento #8 - 33 skills exactas en texto no extraídas)
            # ===================================================================
            # Skills que están EXACTAMENTE en el texto pero no se capturaban
            # Fuente: deep_analysis_missing_skills.py - 71.7% de skills faltantes están en texto
            'exact_missing_skills': [
                # Messaging & Queues
                r'\bIBMMQ\b', r'\bRabbitMQ\b', r'\bRabbit\s+MQ\b',
                # Java ecosystem específico
                r'\bJava\s+\d+\+?\b',  # Java 17+, Java 11+, etc.
                r'\bJPA\b', r'\bSLF4J\b', r'\bSybase\b',
                # Auth & Security
                r'\bOAuth2\b', r'\bOAuth\s+2\b', r'\bAutenticación\b', r'\bSeguridad\b',
                # IDEs completos
                r'\bVisual\s+Studio\s+Code\b', r'\bIntelliJ\s+IDEA\b', r'\bEclipse\b',
                # Frontend frameworks específicos
                r'\bNgRx\b', r'\bRxJS\b',
                # Cloud services específicos
                r'\bGCP\b', r'\bGoogle\s+Cloud\s+Platform\b',
                # Web fundamentals
                r'\bHTML5\b', r'\bHTML\s+5\b',
                # Architecture patterns (español)
                r'\bArquitectura\s+SOA\b', r'\bBases?\s+de\s+datos\s+relacionales\b',
                r'\bBases?\s+de\s+datos\s+no\s+relacionales\b',
                # BI-specific
                r'\bDataflows?\s+Gen2\b', r'\bDAX\s+Studio\b', r'\bLakehouse\b',
                r'\bMicrosoft\s+Fabric\b', r'\bOneLake\b', r'\bParticionado\b',
                r'\bProcedimientos?\s+almacenados?\b', r'\bModelado\s+de\s+datos\b',
                r'\bControl\s+de\s+versiones\b', r'\bIncremental\s+Refresh\b',
                # Infrastructure
                r'\bInfrastructure\s+as\s+Code\b', r'\bObservabilidad\b',
            ],
            # ===================================================================
            # O*NET + ESCO TECHNICAL SKILLS (276 skills - External Taxonomies)
            # ===================================================================
            # Source: O*NET 2024 Hot Technologies + ESCO Critical Tiers (tier0/1/2 + onet_hot_tech + onet_in_demand)
            # NO data leakage - These are external taxonomies, NOT derived from gold standard
            # Includes: Frameworks, languages, tools, platforms, methodologies from industry standards
            'onet_esco_technical_skills': [
                # O*NET Hot Technologies + ESCO Critical Tiers (276 skills)
                # External taxonomies - NO data leakage
                # Source: O*NET 2024 + ESCO tier0/tier1/tier2 critical + onet_hot_tech + onet_in_demand
                r'\bAJAX\b',
                r'\bAPI Design\b',
                r'\bAPI Security\b',
                r'\bASP\.NET Core\b',
                r'\bAWS Lambda\b',
                r'\bAdobe Acrobat\b',
                r'\bAdobe After Effects\b',
                r'\bAdobe Illustrator\b',
                r'\bAdobe InDesign\b',
                r'\bAdobe Photoshop\b',
                r'\bAgile\b',
                r'\bAlteryx software\b',
                r'\bAmazon DynamoDB\b',
                r'\bAmazon Elastic Compute Cloud EC2\b',
                r'\bAmazon Redshift\b',
                r'\bAmazon Simple Storage Service S3\b',
                r'\bAmazon Web Services AWS CloudFormation\b',
                r'\bAnsible software\b',
                r'\bApache Airflow\b',
                r'\bApache Cassandra\b',
                r'\bApache Hadoop\b',
                r'\bApache Hive\b',
                r'\bApache Kafka\b',
                r'\bApache Maven\b',
                r'\bApache Pulsar\b',
                r'\bApache Spark\b',
                r'\bApache Subversion SVN\b',
                r'\bApache Tomcat\b',
                r'\bApple Safari\b',
                r'\bApple iOS\b',
                r'\bApple macOS\b',
                r'\bAtlassian Bitbucket\b',
                r'\bAtlassian Confluence\b',
                r'\bAtlassian JIRA\b',
                r'\bAuth0\b',
                r'\bAuthentication\b',
                r'\bAuthorization\b',
                r'\bAutodesk AutoCAD\b',
                r'\bAutodesk Revit\b',
                r'\bBackend Development\b',
                r'\bBash\b',
                r'\bBehavior-Driven Development\b',
                r'\bBentley MicroStation\b',
                r'\bBigQuery\b',
                r'\bBootstrap\b',
                r'\bBorder Gateway Protocol BGP\b',
                r'\bC\b',
                r'\bC#\b',
                r'\bC\+\+\b',
                r'\bCascading style sheets CSS\b',
                r'\bChef\b',
                r'\bCircleCI\b',
                r'\bCisco Webex\b',
                r'\bClerk\b',
                r'\bCloud Native\b',
                r'\bCloudflare\b',
                r'\bCode Review\b',
                r'\bComputer Vision\b',
                r'\bContainer Orchestration\b',
                r'\bContainerization\b',
                r'\bContentful\b',
                r'\bContinuous Deployment\b',
                r'\bContinuous Integration\b',
                r'\bCypress\b',
                r'\bDart\b',
                r'\bData Infrastructure\b',
                r'\bData Lake\b',
                r'\bData Pipeline\b',
                r'\bData Warehouse\b',
                r'\bDatadog\b',
                r'\bDeep Learning\b',
                r'\bDjango\b',
                r'\bDocker\b',
                r'\bDomain-Driven Design\b',
                r'\bDrupal\b',
                r'\bETL\b',
                r'\bEclipse IDE\b',
                r'\bEclipse Jersey\b',
                r'\bElasticsearch\b',
                r'\bEntity Framework\b',
                r'\bEpic Systems\b',
                r'\bEvent-Driven Architecture\b',
                r'\bExpo\b',
                r'\bExpress\.js\b',
                r'\bExtensible markup language XML\b',
                r'\bFacebook\b',
                r'\bFastAPI\b',
                r'\bFigma\b',
                r'\bFirebase\b',
                r'\bFlask\b',
                r'\bFlutter\b',
                r'\bFrontend Development\b',
                r'\bFull-Stack Development\b',
                r'\bGit\b',
                r'\bGitHub\b',
                r'\bGitHub Actions\b',
                r'\bGitLab\b',
                r'\bGitLab CI\/CD\b',
                r'\bGo\b',
                r'\bGoogle Analytics\b',
                r'\bGoogle Android\b',
                r'\bGoogle Angular\b',
                r'\bGoogle Cloud Platform\b',
                r'\bGoogle Docs\b',
                r'\bGoogle Sheets\b',
                r'\bGrafana\b',
                r'\bGraphQL\b',
                r'\bGraphQL API\b',
                r'\bHelm\b',
                r'\bHeroku\b',
                r'\bHibernate ORM\b',
                r'\bHubSpot software\b',
                r'\bHugging Face\b',
                r'\bHypertext markup language HTML\b',
                r'\bIBM DB2\b',
                r'\bIBM SPSS Statistics\b',
                r'\bIBM Terraform\b',
                r'\bIBM WebSphere MQ\b',
                r'\bInformatica software\b',
                r'\bInfrastructure as Code\b',
                r'\bIonic\b',
                r'\bJUnit\b',
                r'\bJWT\b',
                r'\bJavaScript\b',
                r'\bJavaScript Object Notation JSON\b',
                r'\bJenkins CI\b',
                r'\bJest\b',
                r'\bJupyter Notebook\b',
                r'\bKeras\b',
                r'\bKeycloak\b',
                r'\bKotlin\b',
                r'\bKubernetes\b',
                r'\bLangChain\b',
                r'\bLaravel\b',
                r'\bLinux\b',
                r'\bMEDITECH software\b',
                r'\bMLOps\b',
                r'\bMachine Learning\b',
                r'\bMagento\b',
                r'\bMarketo Marketing Automation\b',
                r'\bMaterial-UI\b',
                r'\bMicroservices\b',
                r'\bMicrosoft \.NET Framework\b',
                r'\bMicrosoft ASP\.NET\b',
                r'\bMicrosoft Access\b',
                r'\bMicrosoft Active Directory\b',
                r'\bMicrosoft Active Server Pages ASP\b',
                r'\bMicrosoft Azure\b',
                r'\bMicrosoft Dynamics\b',
                r'\bMicrosoft Excel\b',
                r'\bMicrosoft Outlook\b',
                r'\bMicrosoft Power BI\b',
                r'\bMicrosoft PowerPoint\b',
                r'\bMicrosoft PowerShell\b',
                r'\bMicrosoft Project\b',
                r'\bMicrosoft SQL Server\b',
                r'\bMicrosoft SQL Server Integration Services SSIS\b',
                r'\bMicrosoft SQL Server Reporting Services SSRS\b',
                r'\bMicrosoft SharePoint\b',
                r'\bMicrosoft Team Foundation Server\b',
                r'\bMicrosoft Teams\b',
                r'\bMicrosoft Visio\b',
                r'\bMicrosoft Visual Basic\b',
                r'\bMicrosoft Visual Studio\b',
                r'\bMicrosoft Windows\b',
                r'\bMicrosoft Windows Server\b',
                r'\bMicrosoft Word\b',
                r'\bMongoDB\b',
                r'\bMozilla Firefox\b',
                r'\bMySQL\b',
                r'\bNATS\b',
                r'\bNatural Language Processing\b',
                r'\bNestJS\b',
                r'\bNetlify\b',
                r'\bNew Relic\b',
                r'\bNext\.js\b',
                r'\bNginx\b',
                r'\bNoSQL\b',
                r'\bNode\.js\b',
                r'\bNumPy\b',
                r'\bNuxt\.js\b',
                r'\bOAuth 2\.0\b',
                r'\bOWASP\b',
                r'\bOracle Database\b',
                r'\bOracle Java\b',
                r'\bOracle Java 2 Platform Enterprise Edition J2EE\b',
                r'\bOracle PL\/SQL\b',
                r'\bOracle PeopleSoft\b',
                r'\bOracle Primavera Enterprise Project Portfolio Management\b',
                r'\bOracle SQL Developer\b',
                r'\bPHP\b',
                r'\bPair Programming\b',
                r'\bPandas\b',
                r'\bPerl\b',
                r'\bPlaywright\b',
                r'\bPostgreSQL\b',
                r'\bPostman\b',
                r'\bPrisma\b',
                r'\bProgressive Web Apps\b',
                r'\bPrometheus\b',
                r'\bPuppet\b',
                r'\bPyTorch\b',
                r'\bPytest\b',
                r'\bPython\b',
                r'\bR\b',
                r'\bREST API\b',
                r'\bRESTful API\b',
                r'\bRabbitMQ\b',
                r'\bReact\b',
                r'\bReact Native\b',
                r'\bReact Testing Library\b',
                r'\bRed Hat Enterprise Linux\b',
                r'\bRed Hat OpenShift\b',
                r'\bRedis\b',
                r'\bRedux\b',
                r'\bReinforcement Learning\b',
                r'\bRemix\b',
                r'\bResponsive Design\b',
                r'\bRuby\b',
                r'\bRuby on Rails\b',
                r'\bRust\b',
                r'\bSAP ERP\b',
                r'\bSAP software\b',
                r'\bSAS\b',
                r'\bSalesforce software\b',
                r'\bSanity\b',
                r'\bScala\b',
                r'\bScikit-learn\b',
                r'\bScrum\b',
                r'\bSelenium\b',
                r'\bSentry\b',
                r'\bSequelize\b',
                r'\bServerless\b',
                r'\bServiceNow\b',
                r'\bShadcn\/ui\b',
                r'\bShell script\b',
                r'\bShopify\b',
                r'\bSingle Page Application\b',
                r'\bSlack\b',
                r'\bSnowflake\b',
                r'\bSplunk Enterprise\b',
                r'\bSpring Boot\b',
                r'\bSpring Framework\b',
                r'\bStrapi\b',
                r'\bStream Processing\b',
                r'\bStripe\b',
                r'\bStructured query language SQL\b',
                r'\bSupabase\b',
                r'\bSvelte\b',
                r'\bSwift\b',
                r'\bTableau\b',
                r'\bTailwind CSS\b',
                r'\bTensorFlow\b',
                r'\bTeradata Database\b',
                r'\bTest-Driven Development\b',
                r'\bThe MathWorks MATLAB\b',
                r'\bTransact-SQL\b',
                r'\bTrimble SketchUp Pro\b',
                r'\bTypeScript\b',
                r'\bUNIX\b',
                r'\bUNIX Shell\b',
                r'\bVercel\b',
                r'\bVite\b',
                r'\bVitest\b',
                r'\bVue\.js\b',
                r'\bWeb Security\b',
                r'\bWebpack\b',
                r'\bWooCommerce\b',
                r'\bWordPress\b',
                r'\bWorkday software\b',
                r'\bYardi software\b',
                r'\bZoom\b',
                r'\bZustand\b',
                r'\bdbt\b',
                r'\bjQuery\b',
                r'\btRPC\b'
            ],
            # ===================================================================
            # CONTEXTUALIZED PATTERNS IN SPANISH (FASE 3 - Mejora Critical)
            # ===================================================================
            # These patterns capture skills with Spanish context words
            # Example: "experiencia en Python" → extracts "Python"
            'contextualized_spanish': [
                # Pattern: "experiencia/conocimiento/manejo + en/de/con + SKILL"
                # Languages
                r'\b(?:experiencia|conocimiento|manejo|dominio|expertise)\s+(?:en|de|con)\s+(Python|Java|JavaScript|TypeScript|Go|Rust|PHP|Ruby|Swift|Kotlin|C\+\+|C#)\b',

                # Databases
                r'\b(?:experiencia|conocimiento|manejo|dominio)\s+(?:en|de|con)\s+(?:bases?\s+de\s+datos\s+)?(PostgreSQL|MySQL|MongoDB|Redis|Oracle|SQL\s+Server|Cassandra|Elasticsearch)\b',

                # Frameworks
                r'\b(?:experiencia|conocimiento|dominio)\s+(?:en|de|con)\s+(React|Angular|Vue\.?js|Django|Flask|FastAPI|Spring|Laravel|Node\.?js|Express\.?js)\b',

                # Cloud
                r'\b(?:experiencia|conocimiento)\s+(?:en|de|con)\s+(AWS|Azure|Google\s+Cloud|GCP|Firebase)\b',

                # DevOps
                r'\b(?:experiencia|conocimiento|manejo)\s+(?:en|de|con)\s+(Docker|Kubernetes|Jenkins|Terraform|Ansible)\b',

                # Pattern: "desarrollo/programación + en/con + SKILL"
                r'\b(?:desarrollo|programación|desarrollo de software|desarrollo web)\s+(?:en|con)\s+(Python|Java|JavaScript|TypeScript|React|Angular|Vue|Django|Flask|Node\.?js)\b',

                # Pattern: "SKILL + avanzado/intermedio/básico"
                r'\b(Python|Java|JavaScript|SQL|PostgreSQL|MySQL|MongoDB|React|Angular|Vue|Docker|Kubernetes|AWS|Azure)\s+(?:avanzado|intermedio|básico|nivel\s+avanzado|nivel\s+intermedio)\b',

                # Pattern: "diseño/arquitectura + de/con + SKILL"
                r'\b(?:diseño|arquitectura|implementación|integración)\s+(?:de|con)\s+(microservicios|APIs?|REST|GraphQL|sistemas\s+distribuidos)\b',

                # Pattern: "administración + de + SKILL"
                r'\b(?:administración|gestión|configuración)\s+de\s+(bases?\s+de\s+datos|servidores|infraestructura|sistemas|redes)\b',
            ],
            # ===================================================================
            # BULLET POINT SEPARATED SKILLS (FASE 3 - Mejora #1, Rev 2)
            # ===================================================================
            # Capture skills separated by bullet points (· or •) and similar separators
            # Example: "Tool · Maven · docker · Spring Boot" → extracts all
            'bullet_point_skills': [
                # Pattern: bullet point + SKILL + (next bullet or end)
                # Now case-insensitive to capture "docker", "kubernetes", etc.
                r'[·•\-]\s*([A-Za-z][A-Za-z0-9\s\.+#\-/]+?)(?=\s*[·•\-]|\s*$|\s*\n)',
                # Also capture after colon: "Tools: Maven, Git, Docker"
                r':\s*([A-Za-z][A-Za-z0-9\s\.+#]+?)(?=\s*,|\s*$|\s*\n)',
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
                    # Handle patterns with capture groups
                    # Example: "experiencia en (Python)" → extract group(1) = "Python"
                    # Example: "· Maven · Spring Boot" → extract group(1) = "Maven", "Spring Boot"
                    if skill_type in ('contextualized_spanish', 'bullet_point_skills'):
                        # Extract skill from capture group
                        raw_skill_text = match.group(1) if match.lastindex else match.group()
                        # Use span of capture group
                        start, end = match.span(1) if match.lastindex else match.span()
                    else:
                        # Standard patterns (no capture groups)
                        raw_skill_text = match.group()
                        start, end = match.span()

                    # EXPERIMENT #9.1: Filter bullet_point_skills stopwords
                    # Skip extraction if it's garbage (prepositions, single letters, HTML/JS)
                    if skill_type == 'bullet_point_skills':
                        cleaned_text = raw_skill_text.lower().strip()
                        # Check exact match
                        if cleaned_text in self.BULLET_STOPWORDS:
                            continue
                        # Check if any stopword is contained (for phrases like "piano analytics")
                        words = cleaned_text.split()
                        if any(word in self.BULLET_STOPWORDS for word in words):
                            continue

                    # CRITICAL: Normalize skill text for ESCO matching
                    # Example: "postgres" → "PostgreSQL", "js" → "JavaScript"
                    normalized_skill_text = self._normalize_skill_text(raw_skill_text)

                    # Get context around the match
                    context_start = max(0, start - 50)
                    context_end = min(len(text), end + 50)
                    context = text[context_start:context_end].strip()

                    skill = RegexSkill(
                        skill_text=normalized_skill_text,  # Store normalized form
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
        """
        Normalize skill text for comparison AND ESCO matching.

        As a Senior NLP Engineer, I'm implementing comprehensive normalization
        to maximize ESCO exact match rate (~300 aliases).

        Strategy:
        - Lowercase input
        - Map common aliases → canonical ESCO form
        - Handle acronyms, versions, special chars
        """
        normalized = text.lower().strip()

        # ============================================================================
        # TECHNICAL ALIASES DICTIONARY (Optimized for ESCO matching)
        # ============================================================================

        # Programming Languages (ESCO-capitalized)
        LANG_ALIASES = {
            'py': 'Python',
            'python': 'Python',
            'js': 'JavaScript',
            'javascript': 'JavaScript',
            'ts': 'TypeScript',
            'typescript': 'TypeScript',
            'golang': 'Go',
            'go': 'Go',
            'java': 'Java',
            'ruby': 'Ruby',
            'php': 'PHP',
            'swift': 'Swift',
            'kotlin': 'Kotlin',
            'rust': 'Rust',
        }

        # Databases (ESCO-capitalized)
        DB_ALIASES = {
            'postgres': 'PostgreSQL',
            'postgresql': 'PostgreSQL',
            'psql': 'PostgreSQL',
            'mysql': 'MySQL',
            'mongo': 'MongoDB',
            'mongodb': 'MongoDB',
            'redis': 'Redis',
            'elasticsearch': 'Elasticsearch',
            'cassandra': 'Cassandra',
        }

        # Frameworks & Libraries (ESCO-capitalized)
        FRAMEWORK_ALIASES = {
            'react': 'React',
            'reactjs': 'React',
            'react.js': 'React',
            'react native': 'React Native',
            'angular': 'Angular',
            'angularjs': 'Angular',
            'angular.js': 'Angular',
            'vue': 'Vue.js',
            'vuejs': 'Vue.js',
            'vue.js': 'Vue.js',
            'django': 'Django',
            'flask': 'Flask',
            'fastapi': 'FastAPI',
            'spring': 'Spring',
            'laravel': 'Laravel',
            'rails': 'Ruby on Rails',
            'ruby on rails': 'Ruby on Rails',
        }

        # Cloud Platforms (ESCO-capitalized)
        CLOUD_ALIASES = {
            'aws': 'AWS',
            'amazon web services': 'AWS',
            'azure': 'Microsoft Azure',
            'microsoft azure': 'Microsoft Azure',
            'gcp': 'Google Cloud Platform',
            'google cloud': 'Google Cloud Platform',
        }

        # DevOps & Tools (ESCO-capitalized)
        DEVOPS_ALIASES = {
            'docker': 'Docker',
            'k8s': 'Kubernetes',
            'kubernetes': 'Kubernetes',
            'jenkins': 'Jenkins',
            'gitlab': 'GitLab',
            'terraform': 'Terraform',
            'ansible': 'Ansible',
        }

        # Data Science & ML (ESCO-capitalized)
        ML_ALIASES = {
            'tensorflow': 'TensorFlow',
            'pytorch': 'PyTorch',
            'pandas': 'Pandas',
            'numpy': 'NumPy',
            'jupyter': 'Jupyter',
            'keras': 'Keras',
        }

        # Version Control (ESCO-capitalized)
        VCS_ALIASES = {
            'git': 'Git',
            'github': 'GitHub',
            'gitlab': 'GitLab',
        }

        # Web Technologies (ESCO-capitalized)
        WEB_ALIASES = {
            'html': 'HTML',
            'html5': 'HTML',
            'css': 'CSS',
            'css3': 'CSS',
            'rest': 'REST',
            'restful': 'REST',
            'graphql': 'GraphQL',
            'soap': 'SOAP',
        }

        # ============================================================================
        # LATAM/Enterprise Technologies (Mejora 2.4 - 2025-01-05)
        # ============================================================================

        # Enterprise Software (common in LATAM)
        ENTERPRISE_ALIASES = {
            'sap': 'SAP',
            'salesforce': 'Salesforce',
            'sap erp': 'SAP ERP',
            'peoplesoft': 'PeopleSoft',
            'servicenow': 'ServiceNow',
            'jira': 'Jira',
            'confluence': 'Confluence',
        }

        # Microsoft Ecosystem (very common in LATAM)
        MICROSOFT_ALIASES = {
            'excel': 'Excel',
            'power bi': 'Power BI',
            'powerbi': 'Power BI',
            'sharepoint': 'SharePoint',
            'office 365': 'Office 365',
        }

        # Testing & Mobile
        TESTING_MOBILE_ALIASES = {
            'selenium': 'Selenium',
            'jest': 'Jest',
            'pytest': 'Pytest',
            'android': 'Android',
            'ios': 'iOS',
            'flutter': 'Flutter',
        }

        # Domain-Specific (Mejora 3.4 - Experimento #7, ampliado en #8)
        DOMAIN_SPECIFIC_ALIASES = {
            # .NET ecosystem
            '.net core': '.NET Core',
            'asp.net core': 'ASP.NET Core',
            'entity framework': 'Entity Framework',
            'entity framework core': 'Entity Framework Core',
            'c#': 'C#',
            'csharp': 'C#',
            # Build tools
            'maven': 'Maven',
            'gradle': 'Gradle',
            'junit': 'JUnit',
            'sonarqube': 'SonarQube',
            # Compound skills
            'ci/cd': 'CI/CD',
            'rest api': 'REST API',
            'oop': 'OOP',
            'poo': 'POO',
            'tdd': 'TDD',
            'bdd': 'BDD',
            'ddd': 'DDD',
            'soa': 'SOA',
            'arquitectura soa': 'Arquitectura SOA',
            # BI & Data
            'power bi': 'Power BI',
            'databricks': 'Databricks',
            'data lake': 'Data Lake',
            'dax': 'DAX',
            'dax studio': 'DAX Studio',
            'lakehouse': 'Lakehouse',
            'onelake': 'OneLake',
            'parquet': 'Parquet',
            'delta': 'Delta',
            'cte': 'CTE',
            'ols': 'OLS',
            'rls': 'RLS',
            # NER-migrated (Experimento #8)
            'api gateway': 'API Gateway',
            'iam': 'IAM',
            'web services': 'Web Services',
            'soap': 'SOAP',
            'soapui': 'SOAPUI',
            'json': 'JSON',
            'ssr': 'SSR',
            'scss': 'SCSS',
            'seo': 'SEO',
            'csrf': 'CSRF',
            'ably': 'Ably',
            'mapbox': 'Mapbox',
            'twilio': 'Twilio',
            'stripe': 'Stripe',
            'sentry': 'Sentry',
            'quarkus': 'Quarkus',
            'logback': 'Logback',
            'scrum': 'Scrum',
            # Missing exact skills (Experimento #8)
            'ibmmq': 'IBMMQ',
            'rabbitmq': 'RabbitMQ',
            'jpa': 'JPA',
            'slf4j': 'SLF4J',
            'sybase': 'Sybase',
            'oauth2': 'OAuth2',
            'oauth 2': 'OAuth2',
            'autenticación': 'Autenticación',
            'seguridad': 'Seguridad',
            'visual studio code': 'Visual Studio Code',
            'intellij idea': 'IntelliJ IDEA',
            'eclipse': 'Eclipse',
            'ngrx': 'NgRx',
            'rxjs': 'RxJS',
            'gcp': 'GCP',
            'html5': 'HTML5',
            'modelado de datos': 'Modelado de datos',
            'observabilidad': 'Observabilidad',
        }

        # Combine all aliases
        ALL_ALIASES = {
            **LANG_ALIASES,
            **DB_ALIASES,
            **FRAMEWORK_ALIASES,
            **CLOUD_ALIASES,
            **DEVOPS_ALIASES,
            **ML_ALIASES,
            **VCS_ALIASES,
            **WEB_ALIASES,
            **ENTERPRISE_ALIASES,
            **MICROSOFT_ALIASES,
            **TESTING_MOBILE_ALIASES,
            **DOMAIN_SPECIFIC_ALIASES,
        }

        # Apply normalization
        return ALL_ALIASES.get(normalized, normalized) 