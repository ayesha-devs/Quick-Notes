FROM nginx:1.27-alpine
ENV APP_HOST=app
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY html/ /usr/share/nginx/html/
EXPOSE 80