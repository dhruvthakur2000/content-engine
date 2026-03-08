from content_engine.backend.ingestion.git_parsar import GitLogService
from content_engine.backend.ingestion.dump_parser import DumpParserService

git_service = GitLogService(repo_path=".")

git_log = git_service.get_git_log(days_back=1)

print(git_log)

parser = DumpParserService()

notes = parser.load_and_parse_dump()

print(notes)