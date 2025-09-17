"""Property path resolvers for StageFlow extensions."""

from abc import ABC, abstractmethod
from typing import Any

from stageflow.core.element import Element


class PropertyResolver(ABC):
    """
    Abstract base class for property path resolvers.

    Property resolvers provide alternative ways to access element data
    beyond the default dot notation.
    """

    @abstractmethod
    def resolve(self, element: Element, path: str) -> Any:
        """
        Resolve property path to value.

        Args:
            element: Element to resolve path in
            path: Property path to resolve

        Returns:
            Resolved value

        Raises:
            KeyError: If path cannot be resolved
        """
        pass

    @abstractmethod
    def exists(self, element: Element, path: str) -> bool:
        """
        Check if property path exists.

        Args:
            element: Element to check
            path: Property path to check

        Returns:
            True if path exists, False otherwise
        """
        pass


class JsonPathResolver(PropertyResolver):
    """
    JSONPath-based property resolver.

    Provides JSONPath syntax for accessing nested data structures
    with more advanced querying capabilities.
    """

    def __init__(self):
        """Initialize JSONPath resolver."""
        try:
            import jsonpath_ng
            self._parser = jsonpath_ng.parse
        except ImportError:
            raise ImportError("jsonpath-ng package required for JSONPath resolver")

    def resolve(self, element: Element, path: str) -> Any:
        """Resolve JSONPath expression to value."""
        data = element.to_dict()
        jsonpath_expr = self._parser(path)
        matches = jsonpath_expr.find(data)

        if not matches:
            raise KeyError(f"JSONPath '{path}' not found")

        # Return first match value
        return matches[0].value

    def exists(self, element: Element, path: str) -> bool:
        """Check if JSONPath expression has matches."""
        try:
            data = element.to_dict()
            jsonpath_expr = self._parser(path)
            matches = jsonpath_expr.find(data)
            return len(matches) > 0
        except Exception:
            return False


class XPathResolver(PropertyResolver):
    """
    XPath-based property resolver for XML-like data structures.

    Provides XPath syntax for accessing nested data when element
    data can be represented as XML.
    """

    def __init__(self):
        """Initialize XPath resolver."""
        try:
            import xml.etree.ElementTree as ET
            self._ET = ET
        except ImportError:
            raise ImportError("xml.etree required for XPath resolver")

    def resolve(self, element: Element, path: str) -> Any:
        """Resolve XPath expression to value."""
        # Convert element data to XML and apply XPath
        # This is a simplified implementation
        data = element.to_dict()
        xml_root = self._dict_to_xml(data, "root")

        results = xml_root.findall(path)
        if not results:
            raise KeyError(f"XPath '{path}' not found")

        # Return text content of first match
        return results[0].text

    def exists(self, element: Element, path: str) -> bool:
        """Check if XPath expression has matches."""
        try:
            data = element.to_dict()
            xml_root = self._dict_to_xml(data, "root")
            results = xml_root.findall(path)
            return len(results) > 0
        except Exception:
            return False

    def _dict_to_xml(self, data: dict[str, Any], root_name: str):
        """Convert dictionary to XML element."""
        root = self._ET.Element(root_name)
        self._dict_to_xml_recursive(data, root)
        return root

    def _dict_to_xml_recursive(self, data: Any, parent):
        """Recursively convert dictionary to XML."""
        if isinstance(data, dict):
            for key, value in data.items():
                child = self._ET.SubElement(parent, str(key))
                self._dict_to_xml_recursive(value, child)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                child = self._ET.SubElement(parent, f"item_{i}")
                self._dict_to_xml_recursive(item, child)
        else:
            parent.text = str(data)


class TemplateResolver(PropertyResolver):
    """
    Template-based property resolver.

    Allows template expressions for computed properties based on
    multiple element fields.
    """

    def __init__(self, template_engine: str = "jinja2"):
        """
        Initialize template resolver.

        Args:
            template_engine: Template engine to use ('jinja2' or 'string')
        """
        self.template_engine = template_engine

        if template_engine == "jinja2":
            try:
                import jinja2
                self._jinja_env = jinja2.Environment()
            except ImportError:
                raise ImportError("jinja2 package required for Jinja2 template resolver")

    def resolve(self, element: Element, path: str) -> Any:
        """Resolve template expression to computed value."""
        data = element.to_dict()

        if self.template_engine == "jinja2":
            template = self._jinja_env.from_string(path)
            return template.render(**data)
        else:
            # Simple string template
            import string
            template = string.Template(path)
            return template.safe_substitute(**data)

    def exists(self, element: Element, path: str) -> bool:
        """Check if template can be resolved without errors."""
        try:
            self.resolve(element, path)
            return True
        except Exception:
            return False


class ResolverRegistry:
    """Registry for managing property resolvers."""

    def __init__(self):
        """Initialize empty resolver registry."""
        self._resolvers: dict[str, PropertyResolver] = {}

    def register(self, name: str, resolver: PropertyResolver):
        """
        Register a property resolver.

        Args:
            name: Unique name for the resolver
            resolver: PropertyResolver instance

        Raises:
            ValueError: If resolver name already exists
        """
        if name in self._resolvers:
            raise ValueError(f"Resolver '{name}' is already registered")

        self._resolvers[name] = resolver

    def unregister(self, name: str):
        """
        Unregister a property resolver.

        Args:
            name: Name of resolver to remove

        Raises:
            KeyError: If resolver doesn't exist
        """
        if name not in self._resolvers:
            raise KeyError(f"Resolver '{name}' is not registered")

        del self._resolvers[name]

    def get_resolver(self, name: str) -> PropertyResolver:
        """
        Get a registered resolver.

        Args:
            name: Name of resolver to retrieve

        Returns:
            PropertyResolver instance

        Raises:
            KeyError: If resolver doesn't exist
        """
        if name not in self._resolvers:
            raise KeyError(f"Resolver '{name}' is not registered")

        return self._resolvers[name]

    def resolve(self, name: str, element: Element, path: str) -> Any:
        """
        Resolve using named resolver.

        Args:
            name: Name of resolver to use
            element: Element to resolve path in
            path: Property path to resolve

        Returns:
            Resolved value

        Raises:
            KeyError: If resolver doesn't exist or path cannot be resolved
        """
        resolver = self.get_resolver(name)
        return resolver.resolve(element, path)

    def exists(self, name: str, element: Element, path: str) -> bool:
        """
        Check existence using named resolver.

        Args:
            name: Name of resolver to use
            element: Element to check
            path: Property path to check

        Returns:
            True if path exists, False otherwise
        """
        try:
            resolver = self.get_resolver(name)
            return resolver.exists(element, path)
        except KeyError:
            return False

    def list_resolvers(self) -> list[str]:
        """
        List all registered resolver names.

        Returns:
            List of resolver names
        """
        return list(self._resolvers.keys())

    def clear(self):
        """Clear all registered resolvers."""
        self._resolvers.clear()


# Global resolver registry instance
_global_resolver_registry = ResolverRegistry()


def register_resolver(name: str, resolver: PropertyResolver):
    """
    Register a resolver in the global registry.

    Args:
        name: Unique name for the resolver
        resolver: PropertyResolver instance
    """
    _global_resolver_registry.register(name, resolver)


def get_global_resolver_registry() -> ResolverRegistry:
    """Get the global property resolver registry."""
    return _global_resolver_registry
