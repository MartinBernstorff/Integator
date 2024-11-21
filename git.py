from abc import ABC

from shell import Shell


class Git(ABC):
    def log(self): ...

    @staticmethod
    def impl() -> "Git":
        return GitImpl()


class GitImpl(Git):
    def log(self):
        values = Shell.impl().run(
            "git log -n 10 --pretty=format:'%C(auto)%h %C(green)%ar %C(auto)%aN %N%-C() ' --date=format:'%H:%M'"
        )

        pass
