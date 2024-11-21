from abc import ABC

from shell import interactive_cmd


class Git(ABC):
    def log(self): ...

    @staticmethod
    def impl() -> "Git":
        return GitImpl()


class GitImpl(Git):
    def log(self):
        interactive_cmd(
            "git log -n 10 --pretty=format:'%C(auto)%h %C(green)%ar %C(auto)%aN %N%-C() ' --date=format:'%H:%M'"
        )
