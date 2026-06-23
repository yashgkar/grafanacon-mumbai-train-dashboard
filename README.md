## How We Built It

* Created a Grafana Cloud account to host and manage the dashboard.
* Added the required data sources and integrated our transportation APIs into Grafana.
* Used the **Grafana Infinity Plugin** to connect to external APIs and fetch data directly within Grafana.
* Configured **HTTP GET requests** to retrieve train transportation data from our API endpoints.
* Leveraged the Infinity Plugin's support for multiple data formats to parse and visualize the API responses.
* Built the dashboard entirely within Grafana using a combination of visualizations such as:

  * Graphs for tracking trends and metrics
  * Tables for displaying detailed train information
  * Gauges with thresholds for quick status indicators
* Applied dashboard styling, panel configurations, and threshold-based visual cues to make the data easy to understand at a glance.
* Combined Grafana's visualization capabilities with real-time API data to create an interactive Mumbai Train Transportation Dashboard.



for more info - checkout our blog here -> https://yashgarudkar.medium.com/building-a-real-time-mumbai-local-train-dashboard-with-grafana-infinity-plugin-7d8134ae1685
