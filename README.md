# JarvisMonitor
Monitor that runs in the background to report the health status of Jarvis and its processes

### Sample Crontab Entry
```bash
* * * * * cd $HOME/JarvisMonitor && bash run.sh >> monitor.log
```

Before making any changes to the `main` branch:
- Cron entry should be commented
- Main branch should be free of any commits made on `docs` branch

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
[2]: https://health.jarvis.services
[3]: https://htmlpreview.github.io/?https://github.com/thevickypedia/JarvisMonitor/blob/docs/docs/index.html
