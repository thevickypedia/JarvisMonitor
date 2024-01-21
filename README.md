# JarvisMonitor
Monitor that runs in the background to report the health status of Jarvis and its processes

### Sample Crontab Entry
```bash
* * * * * cd ~/JarvisMonitor && bash run.sh >> monitor.log
```

Before making any changes to the `main` branch:
- Cron entry should be commented
- Main branch should be free of any commits made on `docs` branch

If git push stops working on crontab:
- Use the following command to authenticate using `SSH` instead of `https`
```shell
git remote set-url origin git@github.com:thevickypedia/JarvisMonitor.git
```

## Sample Report
| Process Name   |  Status   |
|----------------|:---------:|
| Automator      | &#128994; |
| Fastapi        | &#128994; |
| Jarvis         | &#128994; |
| Telegram       | &#128994; |
| Wifi Connector | &#128308; |

## References
- Source Repo: [Jarvis][1]
- Status Page: [Health][2]
- Internal Preview: [Preview][3]

[1]: https://github.com/thevickypedia/Jarvis
[2]: https://jarvis-health.vigneshrao.com
[3]: https://htmlpreview.github.io/?https://github.com/thevickypedia/JarvisMonitor/blob/docs/docs/index.html
