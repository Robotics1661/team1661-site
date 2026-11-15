[![Netlify Status](https://api.netlify.com/api/v1/badges/598aa8f0-a269-41c2-a28e-0e361e639eb9/deploy-status)](https://app.netlify.com/sites/team1661-site-new/deploys)

# team1661-site

Source for [team1661.com](https://team1661.com), the website of Griffitrons 1661, the FIRST Robotics Competition
team at The Buckley School.

A static, build-free site: everything in `src/` is published as-is (see `netlify.toml`).

## Pages

`src/` has the home page plus pages for robots, awards, outreach, media, sponsors and joining the team, and a
custom 404. Shared styles and scripts are in `src/assets/` (`style.css`, `site.js`).

## Running locally

Open `src/index.html` in a browser, or run `npx serve src` to preview locally.

## Deploying

The site is hosted on Netlify, which publishes the `src/` folder as configured in `netlify.toml`. There is no build step.

## Related repos

- [team1661-site-docs](https://github.com/Robotics1661/team1661-site-docs): the team docs at team1661.com/docs

## License

[MIT](LICENSE)
