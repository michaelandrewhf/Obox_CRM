import logging


class IgnoreNoisePathsFilter(logging.Filter):
    IGNORED_PATHS = (
        "/wp-admin",
        "/wordpress",
        "/phpmyadmin",
        "/.env",
    )

    def filter(self, record):
        message = record.getMessage()
        return not any(path in message for path in self.IGNORED_PATHS)


BASE_LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "verbose": {
            "format": (
                "%(asctime)s | %(levelname)s | %(name)s | "
                "%(module)s:%(lineno)d | %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "filters": {
        "ignore_noise_paths": {
            "()": IgnoreNoisePathsFilter,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "filters": ["ignore_noise_paths"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security.DisallowedHost": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "gunicorn.error": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "gunicorn.access": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "obox": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "obox.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "obox.exception": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
