export default function Home() {
  return (
    <div className="flex flex-col flex-1 bg-white dark:bg-black py-12 px-6 md:px-12">
      <main className="w-full max-w-2xl mx-auto">
        <h1>Veggie Rescue Deliveries</h1>
        <p>Welcome to the Veggie Rescue Deliveries platform. This page demonstrates the typeset styling applied globally across your application.</p>

        <h2>Getting Started</h2>
        <p>
          This is a sample markdown-styled page showing how typeset automatically styles all your content—headings, paragraphs, lists, code, tables, and more.
        </p>

        <h3>Key Features</h3>
        <ul>
          <li>Automatic typography styling with Figtree and Inter fonts</li>
          <li>Responsive layout that works on all screen sizes</li>
          <li>Dark mode support built-in</li>
          <li>All markdown elements styled consistently</li>
        </ul>

        <h2>Code Example</h2>
        <p>Here's how to use shadcn/UI components in your app:</p>
        <pre><code>{`import { Button } from "@/components/ui/button"

export function MyComponent() {
  return (
    <Button variant="outline">
      Click me
    </Button>
  )
}`}</code></pre>

        <h2>Deliveries Table</h2>
        <p>Example of how data might be displayed:</p>
        <table>
          <thead>
            <tr>
              <th>Location</th>
              <th>Status</th>
              <th>Items</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Downtown Market</td>
              <td>Scheduled</td>
              <td>12</td>
            </tr>
            <tr>
              <td>East Side Community</td>
              <td>In Progress</td>
              <td>8</td>
            </tr>
            <tr>
              <td>North District</td>
              <td>Completed</td>
              <td>15</td>
            </tr>
          </tbody>
        </table>

        <h2>Blockquote Example</h2>
        <blockquote>
          <p>Food rescue is about connecting surplus food with people who need it. Every delivery makes a difference in our community.</p>
        </blockquote>

        <h2>Lists Demo</h2>
        <h3>Ordered List</h3>
        <ol>
          <li>Check inventory at distribution center</li>
          <li>Pack items into delivery containers</li>
          <li>Route to recipient sites</li>
          <li>Deliver and verify receipt</li>
        </ol>

        <h3>Unordered List</h3>
        <ul>
          <li><strong>Fresh Produce:</strong> Vegetables and fruits</li>
          <li><strong>Proteins:</strong> Meat, dairy, and legumes</li>
          <li><strong>Grains:</strong> Bread, rice, and pasta</li>
          <li><strong>Pantry Items:</strong> Canned goods and dry goods</li>
        </ul>

        <h2>Next Steps</h2>
        <p>
          Replace the content in <code>src/app/page.tsx</code> with your own pages. Check out the other routes in the <code>src/app</code> directory to see how navigation works.
        </p>
        <p>
          All the styling you see here is automatically applied by the typeset classes. Happy building! 🚀
        </p>
      </main>
    </div>
  );
}
