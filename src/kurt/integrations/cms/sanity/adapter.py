"""
Sanity CMS adapter implementation.

Provides interface to Sanity.io CMS using GROQ queries via HTTP API.
"""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from kurt.integrations.cms.base import CMSAdapter, CMSDocument


class SanityAdapter(CMSAdapter):
    """Adapter for Sanity.io CMS using HTTP API."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Sanity client.

        Required config keys:
        - project_id: Sanity project ID
        - dataset: Dataset name (usually 'production')
        - token: Read token for fetching content
        - write_token: Write token for creating drafts (optional)
        - use_cdn: Whether to use CDN (default: False)
        - base_url: Website base URL for constructing document URLs (optional)
        """
        self.project_id = config["project_id"]
        self.dataset = config["dataset"]
        self.token = config.get("token")
        self.write_token = config.get("write_token")
        self.use_cdn = config.get("use_cdn", False)
        self.base_url = config.get("base_url", "")

        # Field mappings from onboarding
        self.mappings = config.get("content_type_mappings", {})

        # Build API URL
        if self.use_cdn:
            self.api_url = (
                f"https://{self.project_id}.apicdn.sanity.io/v2021-10-21/data/query/{self.dataset}"
            )
        else:
            self.api_url = (
                f"https://{self.project_id}.api.sanity.io/v2021-10-21/data/query/{self.dataset}"
            )

        # Mutation API URL (for creating/updating documents)
        self.mutation_url = (
            f"https://{self.project_id}.api.sanity.io/v2021-10-21/data/mutate/{self.dataset}"
        )

    def _query(self, groq_query: str) -> Any:
        """Execute GROQ query against Sanity API."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        params = {"query": groq_query}

        response = requests.get(self.api_url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()
        return data.get("result")

    def _mutate(self, mutations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute mutations (create/update) against Sanity API."""
        if not self.write_token:
            raise ValueError("Write token required for mutations")

        headers = {
            "Authorization": f"Bearer {self.write_token}",
            "Content-Type": "application/json",
        }

        payload = {"mutations": mutations}

        response = requests.post(self.mutation_url, json=payload, headers=headers)
        response.raise_for_status()

        return response.json()

    def test_connection(self) -> bool:
        """Test if Sanity connection is working."""
        try:
            # Simple query to test connection
            self._query('*[_type == "sanity.imageAsset"][0]')
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        content_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[CMSDocument]:
        """
        Search using GROQ query.

        Args:
            query: Text search (searches title and body fields)
            filters: Additional GROQ filters as dict
            content_type: Filter by _type
            limit: Max results

        Returns:
            List of documents (without full content for performance)
        """
        # Build GROQ filter conditions
        groq_filters = []

        if content_type:
            groq_filters.append(f'_type == "{content_type}"')

        if query:
            # Escape quotes in query
            escaped_query = query.replace('"', '\\"')
            groq_filters.append(
                f'(title match "*{escaped_query}*" || ' f'pt::text(body) match "*{escaped_query}*")'
            )

        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    # Array contains
                    groq_filters.append(f'"{value[0]}" in {key}[]')
                elif isinstance(value, str) and value.startswith(">"):
                    # Greater than comparison
                    groq_filters.append(f'{key} > "{value[1:]}"')
                elif isinstance(value, str) and value.startswith("<"):
                    # Less than comparison
                    groq_filters.append(f'{key} < "{value[1:]}"')
                else:
                    # Exact match
                    groq_filters.append(f'{key} == "{value}"')

        filter_clause = " && ".join(groq_filters) if groq_filters else "true"

        # GROQ query - fetch all fields but don't include content body for performance
        # The _to_cms_document method will handle field extraction based on mappings
        groq_query = f"""
        *[{filter_clause}] | order(_updatedAt desc) [0...{limit}] {{
            ...,
            "status": select(
                _id in path("drafts.**") => "draft",
                "published"
            )
        }}
        """

        try:
            results = self._query(groq_query)
            return [self._to_cms_document(doc, include_content=False) for doc in results]
        except Exception as e:
            print(f"Search error: {e}")
            raise

    def list_all(
        self,
        content_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Discover all documents in CMS (for bulk mapping).

        Returns lightweight document metadata without full content.
        Used by 'kurt map cms' for discovery phase.

        Args:
            content_type: Filter by _type (optional)
            status: Filter by status (draft, published) (optional)
            limit: Maximum number of documents to return (optional)

        Returns:
            List of dicts with: id, title, slug, description, content_type, status, updated_at
        """
        # Build GROQ filter conditions
        groq_filters = []

        # Exclude system documents
        # Note: Can't use _id match filters with order() due to Sanity GROQ bug
        # Instead, exclude by system document types
        groq_filters.append('!(_type match "system.*")')
        groq_filters.append('!(_type match "sanity.*")')

        # Only include enabled content types from mappings
        enabled_types = [
            ct_name
            for ct_name, ct_config in self.mappings.items()
            if ct_config.get("enabled", True)
        ]

        if content_type:
            # Filter to specific type if requested
            groq_filters.append(f'_type == "{content_type}"')
        elif enabled_types:
            # Otherwise, only include enabled types
            types_filter = " || ".join([f'_type == "{ct}"' for ct in enabled_types])
            groq_filters.append(f"({types_filter})")

        if status:
            if status.lower() == "draft":
                groq_filters.append('_id in path("drafts.**")')
            elif status.lower() == "published":
                groq_filters.append('!(_id in path("drafts.**"))')

        filter_clause = " && ".join(groq_filters) if groq_filters else "true"

        # Build dynamic field projections for slug and description
        # Use select() to get the right field based on document type
        slug_projection_cases = []
        description_projection_cases = []

        for ct_name, ct_config in self.mappings.items():
            slug_field = ct_config.get("slug_field", "slug.current")
            desc_field = ct_config.get("description_field", "description")

            slug_projection_cases.append(f'_type == "{ct_name}" => {slug_field}')
            description_projection_cases.append(f'_type == "{ct_name}" => {desc_field}')

        # Build select statements with fallbacks
        if slug_projection_cases:
            slug_select = "select(" + ", ".join(slug_projection_cases) + ', "untitled")'
        else:
            slug_select = '"untitled"'

        if description_projection_cases:
            desc_select = "select(" + ", ".join(description_projection_cases) + ", null)"
        else:
            desc_select = "null"

        # GROQ query - lightweight metadata with dynamic field resolution
        limit_clause = f"[0...{limit}]" if limit else ""
        groq_query = f"""
        *[{filter_clause}] | order(_updatedAt desc) {limit_clause} {{
            _id,
            _type,
            _updatedAt,
            title,
            "slug": {slug_select},
            "description": {desc_select},
            "status": select(
                _id in path("drafts.**") => "draft",
                "published"
            )
        }}
        """

        try:
            results = self._query(groq_query)
            return [
                {
                    "id": doc["_id"],
                    "title": doc.get("title", "Untitled"),
                    "slug": doc.get("slug", "untitled"),
                    "description": doc.get("description"),
                    "content_type": doc["_type"],
                    "status": doc.get("status", "published"),
                    "updated_at": doc.get("_updatedAt"),
                }
                for doc in results
            ]
        except Exception:
            raise

    def fetch(self, document_id: str) -> CMSDocument:
        """
        Fetch full document with content.

        Args:
            document_id: Sanity document ID (with or without 'drafts.' prefix)

        Returns:
            Full document with markdown content
        """
        # GROQ query to fetch all fields - the adapter will extract the right ones
        # based on content_type_mappings configuration
        groq_query = f"""
        *[_id == "{document_id}"] {{
            ...,
            "status": select(
                _id in path("drafts.**") => "draft",
                "published"
            )
        }}[0]
        """

        try:
            doc = self._query(groq_query)
            if not doc:
                raise ValueError(f"Document not found: {document_id}")
            return self._to_cms_document(doc, include_content=True)
        except Exception as e:
            print(f"Fetch error: {e}")
            raise

    def fetch_batch(self, document_ids: List[str]) -> List[CMSDocument]:
        """
        Fetch multiple documents in one query.

        Args:
            document_ids: List of Sanity document IDs

        Returns:
            List of full documents with content
        """
        if not document_ids:
            return []

        # Build GROQ query for multiple IDs - fetch all fields
        ids_str = ", ".join(f'"{id}"' for id in document_ids)
        groq_query = f"""
        *[_id in [{ids_str}]] {{
            ...,
            "status": select(
                _id in path("drafts.**") => "draft",
                "published"
            )
        }}
        """

        try:
            docs = self._query(groq_query)
            return [self._to_cms_document(doc, include_content=True) for doc in docs]
        except Exception as e:
            print(f"Batch fetch error: {e}")
            raise

    def create_draft(
        self,
        content: str,
        title: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Create draft in Sanity.

        Args:
            content: Markdown content
            title: Document title
            content_type: Sanity schema type
            metadata: Additional fields (slug, author, tags, etc.)
            document_id: If provided, updates existing doc as draft

        Returns:
            Dictionary with draft_id and draft_url
        """
        # Convert markdown to Sanity portable text blocks
        body_blocks = self._markdown_to_sanity_blocks(content)

        # Build document data
        doc_data = {
            "_type": content_type,
            "title": title,
            "body": body_blocks,
        }

        # Add metadata fields
        if metadata:
            # Handle special fields
            if "slug" in metadata and isinstance(metadata["slug"], str):
                doc_data["slug"] = {"_type": "slug", "current": metadata["slug"]}
            if "author" in metadata:
                doc_data["author"] = {"_type": "reference", "_ref": metadata["author"]}
            if "categories" in metadata:
                doc_data["categories"] = [
                    {"_type": "reference", "_ref": cat_id, "_key": cat_id}
                    for cat_id in metadata["categories"]
                ]
            if "tags" in metadata:
                doc_data["tags"] = metadata["tags"]
            if "seo" in metadata:
                doc_data["seo"] = metadata["seo"]

        try:
            if document_id:
                # Update existing as draft
                clean_id = document_id.replace("drafts.", "")
                draft_id = f"drafts.{clean_id}"
                doc_data["_id"] = draft_id

                mutations = [{"createOrReplace": doc_data}]
            else:
                # Create new draft
                mutations = [{"create": doc_data}]

            result = self._mutate(mutations)
            created_id = result["results"][0]["id"]

            # Build draft URL
            draft_url = self._build_draft_url(created_id, content_type)

            return {"draft_id": created_id, "draft_url": draft_url}

        except Exception as e:
            print(f"Draft creation error: {e}")
            raise

    def get_content_types(self) -> List[Dict[str, Any]]:
        """
        List available content types.

        Returns:
            List of content types with document counts
        """
        groq_query = """
        {
            "types": array::unique(*[]._type)
        }
        """

        try:
            result = self._query(groq_query)
            types = result.get("types", [])

            # Filter out system types
            content_types = [t for t in types if not t.startswith("sanity.")]

            # Get counts for each type
            type_info = []
            for type_name in content_types:
                count_query = f'count(*[_type == "{type_name}"])'
                count = self._query(count_query)
                type_info.append({"name": type_name, "count": count})

            return type_info

        except Exception as e:
            print(f"Error fetching content types: {e}")
            raise

    def get_example_document(self, content_type: str) -> Dict[str, Any]:
        """
        Fetch a sample document of the specified content type.

        Args:
            content_type: Sanity content type name

        Returns:
            Raw document dictionary
        """
        groq_query = f'*[_type == "{content_type}"][0]'

        try:
            doc = self._query(groq_query)
            if not doc:
                raise ValueError(f"No documents found for type: {content_type}")
            return doc
        except Exception as e:
            print(f"Error fetching example document: {e}")
            raise

    def _to_cms_document(self, doc: Dict, include_content: bool = True) -> CMSDocument:
        """Convert Sanity document to unified CMSDocument using field mappings."""
        content_type = doc["_type"]

        # Get field mappings for this content type
        content_field = self._get_content_field(content_type)
        title_field = self._get_title_field(content_type)
        slug_field = self._get_slug_field(content_type)
        metadata_mappings = self._get_metadata_fields(content_type)

        # Extract content using configured field
        content = ""
        if include_content:
            content_data = self._extract_field_value(doc, content_field)
            if content_data:
                if isinstance(content_data, list):
                    # Assume portable text blocks
                    content = self._sanity_blocks_to_markdown(content_data)
                elif isinstance(content_data, str):
                    content = content_data
                else:
                    content = str(content_data)

        # Extract title using configured field
        title = str(self._extract_field_value(doc, title_field) or "")

        # Build URL from slug using configured field
        url = None
        if self.base_url:
            slug_value = self._extract_field_value(doc, slug_field)
            if slug_value:
                url = urljoin(self.base_url, slug_value)

        # Extract metadata using configured mappings
        metadata = {}
        author = None
        published_date = None
        last_modified = None

        for key, field_path in metadata_mappings.items():
            value = self._extract_field_value(doc, field_path)
            if value is not None:
                metadata[key] = value

                # Map to standard fields
                if key == "author":
                    author = value
                elif key == "published_date":
                    published_date = value
                elif key == "last_modified":
                    last_modified = value

        # Add standard system fields if not in mappings
        if not published_date:
            published_date = doc.get("publishedAt")
        if not last_modified:
            last_modified = doc.get("_updatedAt")

        # Add slug to metadata
        slug_value = self._extract_field_value(doc, slug_field)
        if slug_value:
            metadata["slug"] = slug_value

        # Add system fields
        metadata["created_at"] = doc.get("_createdAt")

        return CMSDocument(
            id=doc["_id"],
            title=title,
            content=content,
            content_type=content_type,
            status=doc.get("status", "published"),
            url=url,
            author=author,
            published_date=published_date,
            last_modified=last_modified,
            metadata=metadata,
        )

    def _sanity_blocks_to_markdown(self, blocks: List[Dict]) -> str:
        """Convert Sanity portable text blocks to markdown."""
        if not blocks:
            return ""

        markdown_lines = []

        for block in blocks:
            block_type = block.get("_type", "block")

            if block_type == "block":
                # Standard text block
                style = block.get("style", "normal")
                children = block.get("children", [])

                # Build text from children
                text_parts = []
                for child in children:
                    text = child.get("text", "")
                    marks = child.get("marks", [])

                    # Apply marks
                    for mark in marks:
                        if mark == "strong":
                            text = f"**{text}**"
                        elif mark == "em":
                            text = f"*{text}*"
                        elif mark == "code":
                            text = f"`{text}`"

                    text_parts.append(text)

                line_text = "".join(text_parts)

                # Apply block style
                if style == "h1":
                    markdown_lines.append(f"# {line_text}")
                elif style == "h2":
                    markdown_lines.append(f"## {line_text}")
                elif style == "h3":
                    markdown_lines.append(f"### {line_text}")
                elif style == "h4":
                    markdown_lines.append(f"#### {line_text}")
                elif style == "blockquote":
                    markdown_lines.append(f"> {line_text}")
                else:
                    markdown_lines.append(line_text)

                markdown_lines.append("")  # Empty line after block

            elif block_type == "code":
                # Code block
                code = block.get("code", "")
                language = block.get("language", "")
                markdown_lines.append(f"```{language}")
                markdown_lines.append(code)
                markdown_lines.append("```")
                markdown_lines.append("")

            elif block_type == "image":
                # Image reference
                alt = block.get("alt", "")
                markdown_lines.append(f"![{alt}](sanity-image-{block.get('_key', 'unknown')})")
                markdown_lines.append("")

        return "\n".join(markdown_lines).strip()

    def _markdown_to_sanity_blocks(self, markdown: str) -> List[Dict]:
        """Convert markdown to Sanity portable text blocks."""
        blocks = []
        lines = markdown.split("\n")
        current_paragraph = []

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # Empty line - end current paragraph
            if not line:
                if current_paragraph:
                    blocks.append(self._create_text_block(" ".join(current_paragraph)))
                    current_paragraph = []
                i += 1
                continue

            # Headings
            if line.startswith("# "):
                if current_paragraph:
                    blocks.append(self._create_text_block(" ".join(current_paragraph)))
                    current_paragraph = []
                blocks.append(self._create_text_block(line[2:], style="h1"))
                i += 1
                continue
            elif line.startswith("## "):
                if current_paragraph:
                    blocks.append(self._create_text_block(" ".join(current_paragraph)))
                    current_paragraph = []
                blocks.append(self._create_text_block(line[3:], style="h2"))
                i += 1
                continue
            elif line.startswith("### "):
                if current_paragraph:
                    blocks.append(self._create_text_block(" ".join(current_paragraph)))
                    current_paragraph = []
                blocks.append(self._create_text_block(line[4:], style="h3"))
                i += 1
                continue

            # Code blocks
            if line.startswith("```"):
                if current_paragraph:
                    blocks.append(self._create_text_block(" ".join(current_paragraph)))
                    current_paragraph = []

                language = line[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1

                blocks.append(
                    {
                        "_type": "code",
                        "_key": f"code_{len(blocks)}",
                        "language": language,
                        "code": "\n".join(code_lines),
                    }
                )
                i += 1
                continue

            # Blockquote
            if line.startswith("> "):
                if current_paragraph:
                    blocks.append(self._create_text_block(" ".join(current_paragraph)))
                    current_paragraph = []
                blocks.append(self._create_text_block(line[2:], style="blockquote"))
                i += 1
                continue

            # Regular paragraph line
            current_paragraph.append(line)
            i += 1

        # Add remaining paragraph
        if current_paragraph:
            blocks.append(self._create_text_block(" ".join(current_paragraph)))

        return blocks

    def _create_text_block(self, text: str, style: str = "normal") -> Dict:
        """Create a Sanity text block with inline formatting."""
        children = []

        # Split by formatting marks
        parts = re.split(r"(\*\*.*?\*\*|\*.*?\*|`.*?`)", text)

        for part in parts:
            if not part:
                continue

            marks = []

            # Bold
            if part.startswith("**") and part.endswith("**"):
                part = part[2:-2]
                marks.append("strong")
            # Italic
            elif part.startswith("*") and part.endswith("*"):
                part = part[1:-1]
                marks.append("em")
            # Code
            elif part.startswith("`") and part.endswith("`"):
                part = part[1:-1]
                marks.append("code")

            children.append(
                {"_type": "span", "_key": f"span_{len(children)}", "text": part, "marks": marks}
            )

        return {
            "_type": "block",
            "_key": f"block_{id(text)}",
            "style": style,
            "children": children,
            "markDefs": [],
        }

    def _build_draft_url(self, draft_id: str, content_type: str) -> str:
        """Build Sanity Studio URL for viewing draft."""
        clean_id = draft_id.replace("drafts.", "")
        return (
            f"https://www.sanity.io/manage/personal/"
            f"{self.project_id}/desk/{content_type};{clean_id}"
        )

    def _get_content_field(self, content_type: str) -> str:
        """Get configured content field name for this type."""
        mapping = self.mappings.get(content_type, {})
        return mapping.get("content_field", "body")

    def _get_title_field(self, content_type: str) -> str:
        """Get configured title field name for this type."""
        mapping = self.mappings.get(content_type, {})
        return mapping.get("title_field", "title")

    def _get_slug_field(self, content_type: str) -> str:
        """Get configured slug field name for this type."""
        mapping = self.mappings.get(content_type, {})
        return mapping.get("slug_field", "slug.current")

    def _get_metadata_fields(self, content_type: str) -> Dict[str, str]:
        """Get configured metadata field mappings for this type."""
        mapping = self.mappings.get(content_type, {})
        return mapping.get("metadata_fields", {})

    def _extract_field_value(self, doc: Dict, field_path: str) -> Any:
        """
        Extract field value from document using path notation.

        Supports:
        - Simple fields: "title"
        - Nested fields: "slug.current"
        - References: "author->name"
        - Arrays: "tags[]"
        - Array of references: "categories[]->title"
        """
        if not field_path:
            return None

        # Handle reference resolution
        if "->" in field_path:
            base_path, ref_field = field_path.split("->", 1)
            base_value = self._extract_field_value(doc, base_path)

            if not base_value:
                return None

            # Handle array of references
            if isinstance(base_value, list):
                return [
                    item.get(ref_field)
                    for item in base_value
                    if isinstance(item, dict) and ref_field in item
                ]
            # Handle single reference
            elif isinstance(base_value, dict):
                return base_value.get(ref_field)
            else:
                return None

        # Handle array notation
        if field_path.endswith("[]"):
            base_path = field_path[:-2]
            value = self._extract_field_value(doc, base_path)
            return value if isinstance(value, list) else []

        # Handle nested fields
        parts = field_path.split(".")
        current = doc

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current
