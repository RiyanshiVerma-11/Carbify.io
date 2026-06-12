FROM nginx:alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static assets to nginx html path
COPY src/ /usr/share/nginx/html/

# Expose Nginx port (matching nginx.conf listen port)
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
