# -*- coding: utf-8 -*-
import logging


class GithubParser:

    def __init__(self, data):
        self.data = data
        self.rendered_text = []
        self.status_publish = False

    def process_commit(self):
        def build_files(added, modified, removed):
            added = list(set(added))
            modified = list(set(modified))
            removed = list(set(removed))

            added_text = ""
            modified_text = ""
            removed_text = ""

            if len(added):
                added_text = "\nNew files:\n" + "\n".join(added)

            if len(modified):
                modified_text = "Modified files:\n" + "\n".join(modified)

            if len(removed):
                removed_text = "Removed files:\n" + "\n".join(removed)

            return "\n\n".join([added_text, modified_text, removed_text])

        template = []
        commits = self.data['commits']
        pusher = self.data['pusher']
        ref = self.data['ref']
        repository_name = self.data['repository']['full_name']
        commits_text = "commits" if len(commits) > 1 else "commit"

        if "master" in ref:

            template.append("%s pushed %d %s to %s [%s]:\n" % (pusher['name'],
                                                               len(commits),
                                                               commits_text,
                                                               ref.split('/')[-1],
                                                               repository_name
                                                        ))
            added = []
            modified = []
            removed = []
            for commit in commits:
                template.append("* %s" % commit['message'].rstrip().replace('\r\n\r\n', '\n').replace('\n\n', '\n'))
                added.extend(commit["added"])
                modified.extend(commit["modified"])
                removed.extend(commit["removed"])

            template.append("%s" % build_files(added, modified, removed))
            template.append("%s\n" % self.data['compare'])

        return '\n'.join(template)

    def process_issue(self):
        """
        Builds text message about created/closed issues
        :param issue:
        """
        template = []

        author = self.data['sender']['login']
        issue = self.data['issue']
        action = self.data['action']
        repository_name = self.data['repository']['full_name']

        if action == "opened" or action == "closed":
            template.append("{} {} {} {}issue «<code>{}</code>» [<a href=\"{}\">{}</a>]".format(
                    "👉" if action == "opened" else "✅",
                    author,
                    action,
                    "new " if action == "opened" else "",
                    issue['title'],
                    'https://github.com/' + repository_name,
                    repository_name
            ))
            template.append("\n%s\n" % issue['body']) if len(issue['body']) else template.append("")
            template.append("%s\n" % issue['html_url'])

        if action == 'assigned':
            assignee = self.data['assignee']['login']

            template.append('📌 {author} has assigned {assignee} to issue «<code>{issue_title}</code>» [{repository_name}]'.format(
                author=author,
                assignee=assignee,
                issue_title=issue['title'],
                repository_name=repository_name
            ))
            template.append('')
            template.append(issue['html_url'])

        return '\n'.join(template)

    def process_pull_request(self):
        """
        Builds text message about opened/changed/closed pull request
        :param pull_request: object from github api data
        :param action: pull request action (opened, closed, ...)
        :param author
        :return: message
        """
        template = []

        action = self.data['action']
        author = self.data['sender']['login']
        pull_request = self.data['pull_request']
        repository_name = self.data['repository']['full_name']

        if action == "opened" or action == "closed":
            template.append(
                "😼 {} {} {}pull request <code>«{}»</code> from <b>{}</b> to <b>{}</b> [<a href=\"{}\">{}</a>]".format(
                    author,
                    action,
                    "new " if action == "opened" else "",
                    pull_request['title'],
                    pull_request['head']['ref'],
                    pull_request['base']['ref'],
                    'https://github.com/' + repository_name,
                    repository_name
                )
            )

            template.append("\n%s\n" % pull_request['body']) if len(pull_request['body']) else template.append("")
            template.append("%s\n" % pull_request['html_url'])

        return '\n'.join(template)

    def process(self):
        """
        Render text for sending to a telegram chat
        :param data: Payload from Github webhook (already loaded to the object)
        :return:
        """

        template = []

        if "pull_request" in self.data:
            try:
                template.append(self.process_pull_request())
            except Exception as e:
                logging.error("Pull request Error: [%s]" % e)

        if 'commits' in self.data:
            try:
                template.append(self.process_commit())
            except Exception as e:
                logging.error("Commits Error: [%s]" % e)

        if 'issue' in self.data:
            try:
                template.append(self.process_issue())
            except Exception as e:
                logging.error("Issue Error: [%s]" % e)

        if len(template):
            self.status_publish = True

        self.rendered_text.append('\n'.join(template))

        return len(template)

    def get_output(self):
        return "\n".join(self.rendered_text)
