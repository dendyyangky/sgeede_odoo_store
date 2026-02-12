{
    'name': 'SGEEDE Project Progress',
    'version': '19.0.1.0.0',
    'description': """
    
    Adds percentage-based progress tracking to Projects and Tasks.

    Each task has a manual completion percentage.
    Project completion is calculated automatically as the average of all task percentages.
    Progress updates in real time with no manual action required.
    Displayed directly on the project form for quick visibility.

    """,

    'summary': 'Project and task progress tracking by percentage',
    'author': 'SGEEDE',
    'website': 'https://www.sgeede.com',
    'license': 'LGPL-3',
    'category': 'Project',
    'depends': [
        'base', 'project'
    ],
    'data': [
        'views/project_task_views.xml',
        'views/project_project_views.xml',
    ],
    'images' : ['static/description/banner.gif'],
}
