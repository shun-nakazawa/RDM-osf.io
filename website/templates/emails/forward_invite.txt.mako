<%!
    from website import settings
%>

Hello ${referrer.fullname},

You recently added ${fullname} to "${node.title}". ${fullname} wants to claim their account, but the email address they provided is different from the one you provided.  To maintain security of your project, we are sending the account confirmation to you first.

IMPORTANT: To ensure that the correct person is added to your project please forward the message below to ${fullname}.

After ${fullname} confirms their account, they will be able to contribute to the project.

----------------------

Hello ${fullname},

You have been added by ${referrer.fullname} as a contributor to the project "${node.title}" on the GakuNin RDM. To set a password for your account, visit:

${claim_url}

Once you have set a password, you will be able to make contributions to ${node.title}. You will automatically be subscribed to notification emails for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + 'settings/notifications/'}

Sincerely,

The GakuNin RDM Team


National Institute of Informatics

2-1-2 Hitotsubashi, Chiyoda Ward, Tokyo 101-8430, JAPAN

Privacy Policy: https://meatwiki.nii.ac.jp/confluence/pages/viewpage.action?pageId=32676422


Want more information? Visit https://rdm.nii.ac.jp/ or https://nii.ac.jp/ for information about the GakuNin RDM and its supporting organization, the National Institute of Informatics. Questions? Email rdm_support@nii.ac.jp.
