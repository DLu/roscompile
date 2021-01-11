import shutil
import tempfile

from git import Repo

from ros_introspection.util import get_packages


def single_repo_parse(git_url):
    directory_name = tempfile.mkdtemp()

    Repo.clone_from(git_url, directory_name)

    for package in get_packages(directory_name):
        print(package)

    shutil.rmtree(directory_name)


repos = ['https://github.com/DLu/navigation_layers.git',
         'https://github.com/ros-planning/navigation.git'
         ]


def test_generator():
    for repo in repos:
        yield single_repo_parse, repo


if __name__ == '__main__':
    for repo in repos:
        single_repo_parse(repo)
