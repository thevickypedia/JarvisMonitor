# JarvisMonitor
Monitor that runs in the background to report the health status of Jarvis and its processes

### Sample Crontab Entry
```bash
* * * * * cd ~/JarvisMonitor && python run.py
```

> GitHub workflow trigger is set to trigger on `push` against `docs` branch which will build GitHub pages.

## Sample Report
|      Process Name      |  Status   |
|:----------------------:|:---------:|
|         Jarvis         | &#128994; |
|       Jarvis API       | &#128994; |
|    Background Tasks    | &#128994; |
|  Speech Synthesis API  | &#128308; |

## References
- Source Repo: [Jarvis][1]
- Status Page: [Health][2]
- Internal Preview: [Preview][3]

[1]: https://github.com/thevickypedia/Jarvis
[2]: https://jarvis-health.vigneshrao.com
[3]: https://htmlpreview.github.io/?https://github.com/thevickypedia/JarvisMonitor/blob/docs/docs/index.html
